# BACKEND_API_PATIENT.md

本文档详细说明 **患者管理模块** 的后端实现，包括接口列表、请求/响应格式、数据库交互逻辑与业务约束。

---

## 1. 模块概览

- **模块路径**：`app/api/patient.py`
- **蓝图名称**：`patient_bp`
- **依赖**：
  - `flask`：`Blueprint`, `request`, `jsonify`
  - `app.utils.db.get_db_connection`：获取 MySQL 连接（带连接池）
  - `app.utils.common.format_date`：格式化日期
  - `logging`：记录接口访问与错误日志
  - `datetime.date`：部分年龄相关逻辑会用到

- **主要职责**：
  - 患者信息的查询（支持按 ID 查询 & 分页）；
  - 患者注册（带 ID 唯一性校验）；
  - 患者信息更新；
  - 患者删除（级联删除挂号和病历记录）；
  - 患者统计（总数、性别比例、年龄结构）；
  - 在列表中标记“去过所有科室”的 **VIP 患者**。

---

## 2. 相关数据模型

### 2.1 PATIENTS 表（核心）

摘自 `DATABASE_DESIGN.md` 的设计：

```text
PATIENTS {
    string id PK       "患者编号"
    string name        "姓名"
    string password    "登录密码"
    string gender      "性别（男/女/其他）"
    int    age         "年龄"
    string phone       "电话"
    string address     "地址"
    date   create_time "建档时间"
}
```

### 2.2 关联表

患者删除、统计时会用到其他表：

- `APPOINTMENTS`
  - `patient_id` 外键 → 对应患者的挂号记录。
- `MEDICAL_RECORDS`
  - `patient_id` 外键 → 对应患者的病历记录。
- `PRESCRIPTION_DETAILS`
  - 与 `MEDICAL_RECORDS` 通过外键关联，用于处方细则。
- `DEPARTMENTS`
  - 用于“去过所有科室”的高级查询（关系除法），计算 VIP 患者。

---

## 3. 接口总览

| 方法   | 路径                            | 描述                                                         |
|--------|---------------------------------|--------------------------------------------------------------|
| GET    | `/api/patients`                 | 获取所有患者信息（支持按 ID 查询和分页，标记 VIP）          |
| POST   | `/api/patients`                 | 新增/注册患者（包含 ID 存在性校验）                         |
| PUT    | `/api/patients/<p_id>`          | 更新患者信息                                                 |
| DELETE | `/api/patients/<patient_id>`    | 删除患者（级联删除相关挂号和病历记录）                      |
| GET    | `/api/patients/count`           | 查询患者总数                                                 |
| GET    | `/api/patients/gender_ratio`    | 患者性别比例统计                                             |
| GET    | `/api/patients/age_ratio`       | 患者年龄结构比例统计（青少年/青年/中年/老年）               |

---

## 4. 获取患者列表：GET /api/patients

### 4.1 路由定义

```python
@patient_bp.route('/api/patients', methods=['GET'])
def get_patients():
    ...
```

### 4.2 请求参数（Query String）

- `query`（可选，string）
  - 用于按条件过滤患者，实际实现中主要用于按 **ID** 或简单条件查询；
- `limit`（可选，int）
  - 分页大小；
- `offset`（可选，int）
  - 偏移量；与 `limit` 搭配使用。

> 仅当 **提供了 `limit`** 时，SQL 才会追加 `LIMIT ... OFFSET ...`。

### 4.3 日志行为

- 若提供了 `query`：
  - 记录：`"Request to get patients with query: {query}."`
- 否则：
  - 记录：`"Request to get all patients."`

### 4.4 核心 SQL 逻辑（含高级查询）

该接口使用了一个带关系除法语义的 SQL，用于计算 VIP 患者：

```sql
SELECT 
    p.id, p.name, p.gender, p.age, p.phone, p.address, p.create_time,
    CASE 
        WHEN NOT EXISTS (
            SELECT d.id FROM departments d
            WHERE NOT EXISTS (
                SELECT a.id FROM appointments a
                WHERE a.patient_id = p.id AND a.department_id = d.id
            )
        ) THEN 1 
        ELSE 0 
    END AS is_vip
FROM patients p
-- 可选 WHERE 条件, 例如根据 query 过滤
-- 可选 LIMIT / OFFSET 分页
;
```

含义：

- 对每个患者 `p`，判断是否对 **所有科室 d** 都存在至少一条挂号记录：
  - 若对所有科室都“去过一次”（存在 `appointments.patient_id = p.id AND department_id = d.id`），则 `is_vip = 1`；
  - 否则 `is_vip = 0`；
- 这是典型的“关系除法/全称量词”查询，用来找出“去过所有科室”的特殊患者。

### 4.5 返回结果结构

代码中对查询结果做了字段映射与日期格式化：

```python
data = []
for row in rows:
    data.append({
        "id": row['id'],
        "name": row['name'],
        "gender": row['gender'],
        "age": row['age'],
        "phone": row['phone'],
        "address": row['address'],
        "createTime": format_date(row['create_time']),
        "isVip": bool(row['is_vip'])
    })
```

返回示例：

```json
[
  {
    "id": "P001",
    "name": "张三",
    "gender": "男",
    "age": 28,
    "phone": "13800000000",
    "address": "上海市静安区...",
    "createTime": "2024-01-01",
    "isVip": true
  },
  {
    "id": "P002",
    "name": "李四",
    "gender": "女",
    "age": 35,
    "phone": "13800000001",
    "address": "北京市海淀区...",
    "createTime": "2024-02-01",
    "isVip": false
  }
]
```

### 4.6 错误处理

- 异常时：
  - 记录错误日志：`"Error occurred while fetching patients: %s"`
  - 返回：`500 {"error": "<错误信息>"}`

- `finally` 中关闭 `cursor` / `conn` 并记录 `"Database connection closed."`

---

## 5. 新增/注册患者：POST /api/patients

### 5.1 路由定义

```python
@patient_bp.route('/api/patients', methods=['POST'])
def create_patient():
    ...
```

### 5.2 请求体（JSON）

```json
{
  "id": "P001",
  "name": "张三",
  "password": "可选，不传则默认123456",
  "gender": "男",
  "age": 28,
  "phone": "13800000000",
  "address": "上海市静安区...",
  "createTime": "2024-01-01"
}
```

> `password` 若未提供，将在插入时使用默认值 `"123456"`。

### 5.3 业务流程

1. **记录日志**

   ```python
   logger.info("Request to create a new patient with ID: %s", data.get('id'))
   ```

2. **存在性校验（高级查询：存在性约束）**

   ```python
   check_sql = "SELECT id FROM patients WHERE id = %s"
   cursor.execute(check_sql, (data.get('id'),))
   if cursor.fetchone():
       # 说明该 ID 已存在
       ...
   ```

   - 若 ID 已存在：
     - 记录警告日志；
     - 返回：`{"success": False, "message": "患者ID已存在"}`（具体报文在代码中用中文提示）。

3. **插入新患者**

   核心 INSERT（字段顺序参考源码）：

   ```python
   insert_sql = """
       INSERT INTO patients (id, name, password, gender, age, phone, address, create_time)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
   """
   cursor.execute(
       insert_sql,
       (
           data.get('id'),
           data.get('name'),
           data.get('password', '123456'),  # 默认密码
           data.get('gender'),
           data.get('age'),
           data.get('phone'),
           data.get('address'),
           data.get('createTime')
       )
   )
   ```

4. **提交**

   ```python
   conn.commit()
   logger.info("Patient ID %s registered successfully.", data.get('id'))
   return jsonify({"success": True, "message": "患者注册成功"})
   ```

### 5.4 错误处理

- 发生异常时回滚并返回 500：

  ```python
  conn.rollback()
  logger.error("Error occurred while creating patient: %s", str(e))
  return jsonify({"success": False, "message": str(e)}), 500
  ```

- 确保在 `finally` 中关闭连接。

---

## 6. 更新患者信息：PUT /api/patients/<p_id>

### 6.1 路由定义

```python
@patient_bp.route('/api/patients/<string:p_id>', methods=['PUT'])
def update_patient(p_id):
    ...
```

### 6.2 请求体（JSON）

```json
{
  "name": "新姓名",
  "phone": "新电话",
  "address": "新地址",
  "age": 30
}
```

### 6.3 业务流程

1. 记录请求日志：

   ```python
   logger.info("Received data to update patient: %s", data)
   ```

2. 执行 UPDATE：

   ```python
   sql_patient = """
       UPDATE patients 
       SET name = %s, phone = %s, address = %s, age = %s
       WHERE id = %s
   """
   cursor.execute(sql_patient, (
       data.get('name'),
       data.get('phone'),
       data.get('address'),
       data.get('age'),
       p_id
   ))
   conn.commit()
   ```

3. 返回结果：

   ```python
   logger.info("Patient ID %s information updated successfully.", p_id)
   return jsonify({"success": True, "message": "患者信息更新成功，挂号信息已更新"})
   ```


### 6.4 错误处理

- 异常时回滚，并返回 500；
- 最终关闭连接并写日志。

---

## 7. 删除患者：DELETE /api/patients/<patient_id>

### 7.1 路由定义

```python
@patient_bp.route('/api/patients/<string:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    ...
```


### 7.2 业务目标

- 删除患者时，需要一并清理其关联数据：
  - 所有挂号 `APPOINTMENTS`；
  - 所有病历 `MEDICAL_RECORDS`；
  - 通过数据库级联删除相关处方明细 `PRESCRIPTION_DETAILS`。

### 7.3 详细流程

1. **开启事务**

   ```python
   conn.start_transaction()
   ```

2. **删除挂号记录**

   ```python
   cursor.execute("DELETE FROM appointments WHERE patient_id = %s", (patient_id,))
   logger.info("Deleted %d appointment records for patient %s.", cursor.rowcount, patient_id)
   ```

3. **删除病历记录**

   中间省略部分注释说明：依赖外键级联删除 `PRESCRIPTION_DETAILS`。

   ```python
   cursor.execute("DELETE FROM medical_records WHERE patient_id = %s", (patient_id,))
   logger.info(
       "Deleted %d medical records for patient %s (and cascaded %d prescription details).",
       cursor.rowcount, patient_id, cursor.rowcount
   )
   ```

4. **删除患者本身**

   ```python
   cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
   if cursor.rowcount == 0:
       conn.rollback()
       logger.warning("Patient with ID %s not found for deletion.", patient_id)
       return jsonify({"success": False, "message": "患者不存在或已删除。"}), 404
   ```

5. **提交事务并返回**

   ```python
   conn.commit()
   logger.info("Patient with ID %s and all associated data deleted successfully.", patient_id)
   return jsonify({"success": True, "message": "患者及其所有相关数据删除成功。"}), 200
   ```

### 7.4 异常处理

- 发生异常时回滚事务并返回 500；
- 关闭连接并记录 `"Database connection closed."`

---

## 8. 查询患者总数：GET /api/patients/count

### 8.1 路由定义

```python
@patient_bp.route('/api/patients/count', methods=['GET'])
def get_patient_count():
    ...
```

### 8.2 流程与 SQL

```python
logger.info("Request to get total number of patients.")

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

cursor.execute("SELECT COUNT(*) AS total FROM patients")
result = cursor.fetchone()
total_patients = result['total'] if result else 0

logging.info(f"Total patients fetched: {total_patients}")
return jsonify({"total_patients": total_patients})
```

### 8.3 返回示例

```json
{
  "total_patients": 1234
}
```

---

## 9. 性别比例统计：GET /api/patients/gender_ratio

### 9.1 路由定义

```python
@patient_bp.route('/api/patients/gender_ratio', methods=['GET'])
def get_gender_ratio():
    ...
```

### 9.2 核心 SQL

```sql
SELECT gender, COUNT(*) AS count
FROM patients
GROUP BY gender;
```

### 9.3 映射逻辑

将数据库中存储的中文性别值映射到英文 key：

```python
gender_ratio = {"male": 0, "female": 0, "other": 0}
for row in rows:
    gender = row['gender']
    if gender == '男':
        gender_ratio["male"] = row['count']
    elif gender == '女':
        gender_ratio["female"] = row['count']
    else:
        gender_ratio["other"] = row['count']

logging.info("gender_ratio: %s", gender_ratio)
return jsonify(gender_ratio)
```

### 9.4 返回示例

```json
{
  "male": 600,
  "female": 620,
  "other": 14
}
```

---

## 10. 年龄结构统计：GET /api/patients/age_ratio

### 10.1 路由定义

```python
@patient_bp.route('/api/patients/age_ratio', methods=['GET'])
def get_age_ratio():
    ...
```

### 10.2 核心 SQL（按年龄段分组）

```sql
SELECT 
    CASE
        WHEN age BETWEEN 0 AND 18 THEN '青少年'
        WHEN age BETWEEN 19 AND 35 THEN '青年'
        WHEN age BETWEEN 36 AND 60 THEN '中年'
        ELSE '老年'
    END AS age_group,
    COUNT(*) AS count
FROM patients
GROUP BY age_group;
```

### 10.3 返回逻辑

- 若没有任何结果（空表）：

  ```python
  if not rows:
      return jsonify({"青少年": 0, "青年": 0, "中年": 0, "老年": 0})
  ```

- 否则构建统计字典：

  ```python
  age_ratio = {"青少年": 0, "青年": 0, "中年": 0, "老年": 0}
  for row in rows:
      age_group = row['age_group']
      age_ratio[age_group] = row['count']

  logging.info("age_ratio: %s", age_ratio)
  return jsonify(age_ratio)
  ```

### 10.4 返回示例

```json
{
  "青少年": 120,
  "青年": 800,
  "中年": 500,
  "老年": 214
}
```

---

## 11. 统一错误处理与资源释放

在本模块中，各接口都遵循类似结构：

- `try` 中是业务逻辑；
- `except Exception as e`：
  - 写 error 日志；
  - 需要时回滚事务；
  - 返回 `500` 和错误信息；
- `finally`：
  - 关闭 `cursor` / `conn`；
  - 记录 `"Database connection closed."`。

这种模式保证了：

- 失败时数据库状态回滚；
- 即使发生异常也不会泄露连接。

---
