# BACKEND_API_STATS.md

---

## 1. 模块概览

- **文件路径**：`app/api/stats.py`  
- **蓝图名称**：`stats_bp`  
- **依赖模块**：
  - `flask`：`Blueprint`, `request`, `jsonify`
  - `app.utils.db.get_db_connection`
  - `datetime`：`date`, `datetime`
  - `re`：用于校验和解析时间字符串（如 `YYYY-MM`）
  - `logging`：模块级日志

- **提供接口**（来自 `API_DOCUMENTATION.md`）：

| 文件名     | 接口路径                    | 方法 | 描述                                   |
|-----------|-----------------------------|------|----------------------------------------|
| `stats.py` | `/api/stats/sankey`         | GET  | 统计用于绘制桑基图的患者流转数据       |
| `stats.py` | `/api/statistics/monthly`   | GET  | 按月份计算患者/就诊人数及环比增长率    |

---

## 2. 数据来源与统计模型

### 2.1 基础业务表

统计模块主要基于以下表做聚合：

- `APPOINTMENTS`（挂号）
- `MEDICAL_RECORDS`（病历）
- `PATIENTS`（患者）
- `DEPARTMENTS`（科室）
- `DOCTORS`（医生）

常见统计维度：

- 时间：年 / 月 / 日（字段如 `create_time`、`visit_date` 等）
- 对象：患者 / 医生 / 科室
- 指标：挂号数量、就诊数量、面向某科室或某诊断的数量

### 2.2 桑基图数据（Sankey）

配合 `insert_data_python/insert_sankey.py`，系统会预先生成一批“流转”类数据，用于展示患者在不同节点之间的流动关系，例如：

- 患者来源渠道 → 科室 → 诊断 → 结局
- 门诊科室 → 住院科室
- 初诊 → 复诊/转诊 等

这些数据可以直接来自业务表的聚合，也可以落在一张专门的统计表中（如“患者流转表”），本设计文档中不强依赖具体表名，而以“节点(node) + 连接(link)”的抽象为主。

#### 2.2.1 输出结构（前端友好格式）

典型的桑基图数据结构如下：

```json
{
  "nodes": [
    { "name": "门诊" },
    { "name": "心血管内科" },
    { "name": "呼吸内科" },
    { "name": "住院" }
  ],
  "links": [
    { "source": 0, "target": 1, "value": 120 },
    { "source": 0, "target": 2, "value": 80 },
    { "source": 1, "target": 3, "value": 40 }
  ]
}
```

- `nodes[i].name`：节点名称
- `links[j].source` / `links[j].target`：节点索引（指向 `nodes` 数组下标）
- `links[j].value`：对应流量（人数/次数）

前端可以直接用 ECharts、D3 等库渲染。

### 2.3 月度统计数据（Monthly Statistics）

接口 `/api/statistics/monthly` 需要计算按月的：

- **患者数**（或患者新增数）
- **就诊数**（挂号 / 完成就诊数）
- **环比增长率**（Month-over-Month, MoM）

常见输出字段：

| 字段名           | 说明                                |
|------------------|-------------------------------------|
| `month`          | 月份字符串，例如 `"2025-01"`       |
| `patientCount`   | 当月的患者数量（或新增患者数）      |
| `visitCount`     | 当月的就诊次数（或挂号/病历数）     |
| `momPatientRate` | 患者数环比增长率（相对上月）        |
| `momVisitRate`   | 就诊数环比增长率                    |


---

## 3. 接口设计详解

---

### 3.1 桑基图统计接口

- **URL**：`GET /api/stats/sankey`
- **功能**：返回患者流转的桑基图结构，用于可视化“从 A 流向 B 的人数/次数”。

#### 3.1.1 请求参数（建议）

目前代码里没有在 `API_DOCUMENTATION.md` 中列出参数，但从实际需求看，可以支持以下可选参数（即便现在实现中可能只做了默认周期）：

| 参数名        | 类型   | 是否必填 | 示例        | 说明                                   |
|--------------|--------|----------|------------|----------------------------------------|
| `startDate`  | string | 否       | `2025-01-01` | 统计起始日期（含）                     |
| `endDate`    | string | 否       | `2025-12-31` | 统计结束日期（含）                     |
| `dimension`  | string | 否       | `dept-flow` | 流转类型，例如 `dept-flow`, `diag-flow` |
| `maxNodes`   | int    | 否       | `20`       | 限制节点最大数量（聚合尾部为“其他”）   |

如果当前实现没有这些参数，本节可视为“接口升级设计”。

#### 3.1.2 处理流程（设计说明）

1. **解析并校验参数**
   - 若 `startDate` / `endDate` 缺省，则采用默认时间范围（如最近一年或全部数据）；
   - 使用 `datetime.strptime` 校验日期格式。

2. **查询数据库**
   - 根据统计维度，选择不同的聚合方式，例如：
     - 从 `APPOINTMENTS` / `MEDICAL_RECORDS` 中统计“科室 → 诊断结果”的流转；
     - 或根据 `insert_sankey.py` 中写入的统计表进行聚合。
   - 对于每种流转关系，得到：
     - `from_node`，`to_node`，`count`。

3. **构造 `nodes` 数组与索引映射**
   - 将所有出现的 `from_node`、`to_node` 去重，生成 `nodes` 列表；
   - 为每个节点分配一个下标 `index`，例如使用字典 `name_to_index`。

4. **构造 `links` 数组**
   - 对每一条流转记录，根据 `name_to_index` 找到 `source` 与 `target`；
   - 将 `value` 设为人数/次数。

5. **返回 JSON**

```json
{
  "success": true,
  "data": {
    "nodes": [...],
    "links": [...]
  }
}
```

#### 3.1.3 成功响应示例

```json
{
  "success": true,
  "data": {
    "nodes": [
      { "name": "门诊" },
      { "name": "心血管内科" },
      { "name": "呼吸内科" },
      { "name": "住院" }
    ],
    "links": [
      { "source": 0, "target": 1, "value": 120 },
      { "source": 0, "target": 2, "value": 80 },
      { "source": 1, "target": 3, "value": 40 }
    ]
  }
}
```

#### 3.1.4 失败响应示例

- 数据库异常 / 其他异常：

```json
{
  "success": false,
  "message": "Error fetching sankey statistics"
}
```

或当前代码风格中的：

```json
{
  "error": "错误信息"
}
```

并返回 HTTP 500。

---

### 3.2 月度统计接口

- **URL**：`GET /api/statistics/monthly`
- **功能**：按月统计患者数和就诊数，并计算环比增长率。

#### 3.2.1 请求参数

从 `stats.py` 导入的模块看，存在：

- `from datetime import date, datetime`
- `import re`

这通常用来**解析和校验月份字符串**，例如 `2025-01`：

| 参数名        | 类型   | 是否必填 | 示例        | 说明                                   |
|--------------|--------|----------|------------|----------------------------------------|
| `month`      | string | 否       | `2025-01`  | 统计某一指定月份及其前后月份的对比     |
| `range`      | int    | 否       | `6`        | 向前回溯的月份数（如最近 6 个月）      |

**常见设计模式：**

1. **无 `month` 参数**
   - 以当前月份为基准，向前回溯 `6` 或 `12` 个月；
2. **有 `month` 参数**
   - 使用正则 `r'^\d{4}-\d{2}$'` 校验；
   - 将其解析为 `datetime(year, month, 1)`；
   - 以该月为结束月，向前回溯 N 个月。

#### 3.2.2 统计逻辑

1. **构造月份列表**
   - 例如，从 `2025-01` 到 `2025-06`；
   - 对每个月，计算其起始日期和结束日期：

     ```python
     start_date = datetime(year, month, 1)
     # 下个月的 1 号减 1 秒作为当月结束
     ```

2. **查询患者与就诊数量**
   - 对于每个月：
     - 在 `PATIENTS` 中统计新增患者数（或累计数）；
     - 在 `APPOINTMENTS` / `MEDICAL_RECORDS` 中统计挂号/就诊数；
   - SQL 示例（按某个月访问量统计）：

     ```sql
     SELECT COUNT(*) FROM APPOINTMENTS
     WHERE create_time >= %s AND create_time < %s;
     ```

3. **计算环比**
   - 对从第二个月开始的每个月：

     ```python
     mom_patient = (curr_patient - prev_patient) / prev_patient if prev_patient > 0 else None
     mom_visit   = (curr_visit - prev_visit) / prev_visit if prev_visit > 0 else None
     ```

   - 将结果格式化为浮点数或百分比字符串（例如 `0.12` 或 `"12.0%"`）。

4. **组织响应数据**

```json
{
  "success": true,
  "data": [
    {
      "month": "2025-01",
      "patientCount": 120,
      "visitCount": 200,
      "momPatientRate": null,
      "momVisitRate": null
    },
    {
      "month": "2025-02",
      "patientCount": 135,
      "visitCount": 230,
      "momPatientRate": 0.125,
      "momVisitRate": 0.15
    }
  ]
}
```

#### 3.2.3 正则校验与错误处理

- 利用 `re` 模块校验 `month` 字符串格式：

  ```python
  pattern = r'^\d{4}-\d{2}$'
  if month_str and not re.match(pattern, month_str):
      return jsonify({"error": "Invalid month format, expected YYYY-MM"}), 400
  ```

- 当解析失败或日期不合法时，返回 400 错误。

#### 3.2.4 失败响应示例

- 月份格式不正确：

```json
{
  "error": "Invalid month format, expected YYYY-MM"
}
```

- 数据库异常：

```json
{
  "error": "Error fetching monthly statistics"
}
```

---

## 4. 代码结构与资源管理

`stats.py` 中每个接口函数（例如 `get_patient_flow_sankey`、`get_monthly_statistics`）都采用了典型的结构：

```python
conn = None
cursor = None
try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ... 执行 SQL 与组装结果 ...

    return jsonify(res)  # 或 {"success": true, "data": ...}

except Exception as e:
    logger.error("Error fetching ... %s", str(e))
    return jsonify({"error": str(e)}), 500

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    logger.info("Database connection closed for ...")
```

特征：

- **统一的资源释放**：无论成功与否，都在 `finally` 中关闭 `cursor` / `conn`；
- **日志记录**：
  - `logger.error(...)`：在异常发生时记录错误；
  - `logger.info(...)`：记录连接关闭等信息，便于排查连接泄露。

---

## 5. 与其他模块的关系

- **与 `insert_data_python/insert_sankey.py`**
  - 初始化了用于桑基图的示例数据；
  - `stats.py` 的 `/api/stats/sankey` 可直接基于这些数据进行汇总。

- **与基础业务模块**
  - `APPOINTMENTS` / `MEDICAL_RECORDS` / `PATIENTS` 等表由 `appointment.py` / `record.py` / `patient.py` 管理；
  - `stats.py` 不修改业务数据，仅做读取与聚合。

- **与前端可视化**
  - `sankey` 接口为前端提供直接可绘制的数据结构；
  - `monthly` 接口为折线图、柱状图等提供时间序列数据。

---

## 6. 后续扩展建议

1. **统一返回格式**
   - 建议统一为：

     ```json
     { "success": true/false, "data": ..., "message": "..." }
     ```

   - 而不是有的接口返回 `{"error": ...}`，有的返回 `{"success": false}`。

2. **可配置统计维度**
   - 为 `/api/stats/sankey` 增加 `dimension` 参数：
     - `dept-flow`：科室流转
     - `diag-flow`：诊断流转
     - `source-flow`：来源渠道流转
   - 根据不同维度选用不同的 SQL 聚合。

3. **缓存 / 预计算**
   - 对于统计接口访问频繁的情况，可以：
     - 将计算结果缓存到 Redis；
     - 或通过定时任务预计算写入统计表，接口直接读取。

4. **权限控制**
   - 如果统计结果涉及敏感数据（如按医生、按疾病的具体数据），建议结合 `auth.py` 的角色信息控制访问。

5. **国际化与多语言支持**
   - `nodes.name` 等字段若用于多语言界面，可引入字典翻译表或前端本地化方案。

---
