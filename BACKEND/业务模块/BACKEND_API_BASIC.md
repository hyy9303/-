# BACKEND_API_BASIC.md

## 1. 模块概览

- **模块路径**：`app/api/basic.py`  
- **蓝图名称**：`basic_bp`  
- **主要职责**：
  - 提供系统“基础数据”的统一访问接口：
    - 科室（departments）
    - 药品（medicines）
  - 封装常用查询与安全删除逻辑，为挂号、病历、处方等核心业务提供基础信息。

### 1.1 依赖说明

- Flask 相关：
  - `from flask import Blueprint, request, jsonify`
- 数据库连接：
  - `from app.utils.db import get_db_connection`
- 日志：
  - `import logging`
  - `logger = logging.getLogger(__name__)`

---

## 2. 科室接口（Departments）

### 2.1 获取所有科室

- **接口**：`GET /api/departments`
- **函数**：`get_departments()`

#### 业务行为

1. 记录访问日志：
   - `logger.info("Request to get all departments.")`
2. 获取数据库连接：
   - `conn = get_db_connection()`
   - `cursor = conn.cursor(dictionary=True)`
3. 执行 SQL：
   ```sql
   SELECT id, name, location FROM departments;
   ```
4. 获取查询结果：
   - `result = cursor.fetchall()`
5. 记录条数日志：
   - `logger.info("Fetched %d departments from the database.", len(result))`
6. 返回 JSON：
   - 直接将 `result`（字典列表）通过 `jsonify(result)` 返回。

#### 异常处理与资源回收

- `except`：
  - 输出错误日志：`logger.error("Error occurred while fetching departments: %s", str(e))`
  - 返回：`{"error": "...error message..."}`，HTTP 500
- `finally`：
  - 关闭 `cursor` 和 `conn`
  - 日志：`logger.info("Database connection closed.")`

---

### 2.2 获取科室详情（附带医生数量）

- **接口**：`GET /api/departments/<string:department_id>`
- **函数**：`get_department_detail(department_id)`

#### 请求参数

- 路径参数：`department_id`（字符串）

#### 业务行为

1. 记录访问日志：
   - `logger.info("Request to get department detail: %s", department_id)`
2. 获取连接与游标：
   - `cursor = conn.cursor(dictionary=True)`
3. 执行 SQL（含子查询统计该科室医生数）：

   ```sql
   SELECT d.id,
          d.name,
          d.location,
          (SELECT COUNT(*) FROM doctors doc
           WHERE doc.department_id = d.id) AS doctor_count
   FROM departments d
   WHERE d.id = %s;
   ```

4. 读取一条记录：
   - `row = cursor.fetchone()`
5. 若未找到：
   - 记录 warning 日志；
   - 返回 `{"success": False, "message": "科室不存在"}`，HTTP 404。
6. 若找到：
   - 组装返回数据（源码中关键字段）：
     - `id`
     - `name`
     - `location`
     - `doctorCount`（将 `row['doctor_count']` 转为 `int`）
   - `return jsonify(data)`

#### 异常与资源回收

- `except`：
  - `logger.error("Error fetching department %s: %s", department_id, str(e))`
  - 返回：`{"error": "...error..."}`, HTTP 500
- `finally`：
  - 关闭 `cursor`、`conn`
  - 日志：`logger.info("Database connection closed.")`

---

### 2.3 删除科室（有医生禁止删除）

- **接口**：`DELETE /api/departments/<string:department_id>`
- **函数**：`delete_department(department_id)`

#### 业务规则

> **必须满足：该科室下医生数量为 0，才能删除。**

#### 业务行为

1. 记录请求日志：
   - `logger.info("Request to delete department with ID: %s", department_id)`
2. 获取连接、游标（普通 cursor）；
3. 先检查该科室是否仍有关联医生：

   ```sql
   SELECT COUNT(*) FROM doctors WHERE department_id = %s;
   ```

   - 取第一列为 `doctor_count`。

4. 若 `doctor_count > 0`：
   - 记录警告日志（医生数量会写入日志）；
   - 返回：
     ```json
     {
       "success": false,
       "message": "无法删除：该科室下仍有医生。请先移除所有医生。"
     }
     ```
     HTTP 400。

5. 若 `doctor_count == 0`：
   - 执行删除操作（源码中省略号未展示，但语义上为）：
     ```sql
     DELETE FROM departments WHERE id = %s;
     ```
   - 若 `cursor.rowcount == 0`：
     - 可以回滚（源码中有 `conn.rollback()` 逻辑）；
     - 返回“科室不存在或已删除”的错误。
   - 否则：
     - `conn.commit()`
     - 记录 info 日志：删除成功
     - 返回 `{"success": True, "message": "科室删除成功"}`（具体文案以代码实际为准）

#### 异常与资源回收

- `except`：
  - 若 `conn` 存在则 `conn.rollback()`
  - 记录错误日志：`logger.error("Error deleting department %s: %s", department_id, str(e))`
  - 返回：`{"success": False, "message": str(e)}`, HTTP 500
- `finally`：
  - 关闭 `cursor` 和 `conn`
  - 日志：`logger.info("Database connection closed for department deletion.")`

---

## 3. 药品接口（Medicines）

### 3.1 获取所有药品

- **接口**：`GET /api/medicines`
- **函数**：`get_medicines()`

#### 业务行为

1. 记录访问日志：
   - `logger.info("Request to get all medicines.")`
2. 获取连接、字典游标；
3. 执行 SQL：

   ```sql
   SELECT id, name, price, stock, specification FROM medicines;
   ```

4. 获取全部结果 `rows = cursor.fetchall()`；
5. 为了防止 MySQL `Decimal` 直接序列化失败，对每条记录做处理：

   ```python
   for row in rows:
       row['price'] = float(row['price'])
   ```

6. 返回 `jsonify(rows)`。

#### 异常与资源回收

- `except`：
  - 记录错误日志：
    - `logger.error("Error occurred while fetching medicines: %s", str(e))`
  - 返回：`{"error": "...error..."}`, HTTP 500
- `finally`：
  - 关闭 `cursor`、`conn`
  - 日志：`logger.info("Database connection closed.")`

---

### 3.2 获取单个药品详情

- **接口**：`GET /api/medicines/<string:medicine_id>`
- **函数**：`get_medicine_detail(medicine_id)`

#### 请求参数

- 路径参数：`medicine_id`（字符串）

#### 业务行为

1. 记录访问日志：
   - `logger.info("Request to get medicine detail: %s", medicine_id)`
2. 获取连接、字典游标；
3. 执行 SQL：

   ```sql
   SELECT id, name, price, stock, specification
   FROM medicines
   WHERE id = %s;
   ```

4. `row = cursor.fetchone()`：
   - 若 `row is None`：
     - `logger.warning("Medicine %s not found.", medicine_id)`
     - 返回：
       ```json
       { "success": false, "message": "药品不存在" }
       ```
       HTTP 404
   - 若存在：
     - 将 `row['price']` 转为 `float`（与列表接口保持一致）
     - 封装返回数据字典：
       - `id`
       - `name`
       - `price`
       - `stock`
       - `specification`
     - `return jsonify(data)`

#### 异常与资源回收

- `except`：
  - `logger.error("Error fetching medicine %s: %s", medicine_id, str(e))`
  - 返回：`{"error": str(e)}`, HTTP 500
- `finally`：
  - 关闭 `cursor`、`conn`
  - 日志：`logger.info("Database connection closed.")`

---

### 3.3 更新药品信息（部分字段可选）

- **接口**：`PUT /api/medicines/<string:medicine_id>`
- **函数**：`update_medicine_detail(medicine_id)`

#### 请求体

- **Content-Type**：`application/json`
- 支持字段（全部为可选）：
  - `name`：药品名称
  - `price`：价格
  - `stock`：库存
  - `specification`：规格

示例：

```json
{
  "name": "阿司匹林",
  "price": 9.9,
  "stock": 100,
  "specification": "100mg*20片"
}
```

#### 业务行为

1. 读取 JSON：
   - `data = request.json or {}`
2. 记录日志：
   - `logger.info("Request to update medicine %s: %s", medicine_id, data)`
3. 动态组装更新字段：

   ```python
   fields = []
   params = []
   if 'name' in data:
       fields.append("name = %s")
       params.append(data.get('name'))
   if 'price' in data:
       fields.append("price = %s")
       params.append(data.get('price'))
   if 'stock' in data:
       fields.append("stock = %s")
       params.append(data.get('stock'))
   if 'specification' in data:
       fields.append("specification = %s")
       params.append(data.get('specification'))
   ```

4. 若 `fields` 为空（没有任何可更新字段）：
   - 返回：
     ```json
     { "success": false, "message": "没有提供可更新字段" }
     ```
     HTTP 400

5. 拼装 SQL：

   ```python
   sql = "UPDATE medicines SET " + ", ".join(fields) + " WHERE id = %s"
   params.append(medicine_id)
   cursor.execute(sql, tuple(params))
   ```

6. 根据 `cursor.rowcount` 判断是否更新成功：
   - 若 `rowcount == 0`：
     - 可以回滚；
     - 返回“药品不存在或未更新”；
   - 否则：
     - `conn.commit()`
     - 返回：
       ```json
       { "success": true, "message": "药品信息更新成功" }
       ```
       HTTP 200

#### 异常与资源回收

- `except`：
  - 有连接则回滚：`conn.rollback()`
  - 记录错误日志：
    - `logger.error("Error updating medicine %s: %s", medicine_id, str(e))`
  - 返回：`{"success": False, "message": str(e)}`, HTTP 500
- `finally`：
  - 关闭 `cursor`、`conn`
  - 日志：`logger.info("Database connection closed for medicine update.")`

---

### 3.4 删除药品（有处方细则禁止删除）

- **接口**：`DELETE /api/medicines/<string:medicine_id>`
- **函数**：`delete_medicine(medicine_id)`

#### 业务规则

> **若该药品在任何处方明细（`prescription_details`）中被引用，则不允许删除。**

#### 业务行为

1. 记录请求日志：
   - `logger.info("Request to delete medicine with ID: %s (simple logic).", medicine_id)`
2. 获取连接、游标；
3. 查询处方明细引用数量：

   ```sql
   SELECT COUNT(*) FROM prescription_details WHERE medicine_id = %s;
   ```

4. 若 `prescription_detail_count > 0`：
   - 记录 warning 日志；
   - 返回：
     ```json
     {
       "success": false,
       "message": "无法删除：该药品仍有关联的处方细则。请先处理相关处方。"
     }
     ```
     HTTP 400

5. 若 `prescription_detail_count == 0`：
   - 执行删除药品：

     ```sql
     DELETE FROM medicines WHERE id = %s;
     ```

   - 若 `cursor.rowcount == 0`：
     - `conn.rollback()`
     - 记录 warning 日志：药品不存在
     - 返回：
       ```json
       { "success": false, "message": "药品不存在或已删除。" }
       ```
       HTTP 404
   - 否则：
     - `conn.commit()`
     - 记录 info 日志：删除成功
     - 返回：
       ```json
       { "success": true, "message": "药品删除成功" }
       ```
       HTTP 200

#### 异常与资源回收

- `except`：
  - 若 `conn` 存在则回滚；
  - 记录错误日志：
    - `logger.error("Error deleting medicine %s: %s", medicine_id, str(e))`
  - 返回：`{"success": False, "message": str(e)}`, HTTP 500
- `finally`：
  - 关闭 `cursor` 和 `conn`
  - 日志：`logger.info("Database connection closed for medicine deletion.")`

---

## 4. 模块设计特点
- 所有接口都：
  - 显式获取 / 关闭数据库连接；
  - 使用 `try / except / finally` 保证资源释放；
  - 使用 `logging` 记录详细日志（请求、结果数量、错误）。
- 删除操作前都带有**业务约束检查**：
  - 科室删除前检查医生数量；
  - 药品删除前检查处方明细数量。


---
