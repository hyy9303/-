# BACKEND_API_DOCTOR.md

本文档详细说明 **医生管理模块** 的后端实现，包括接口列表、请求/响应格式、数据库交互逻辑与业务约束。

---

## 1. 模块概览

- **模块路径**：`app/api/doctor.py`
- **蓝图名称**：`doctor_bp`
- **依赖**：
  - `flask`：`Blueprint`, `request`, `jsonify`
  - `app.utils.db.get_db_connection`：获取 MySQL 连接（带连接池）
  - `logging`：记录接口访问与错误日志
- **主要职责**：
  - 提供医生信息的查询、修改、删除接口；
  - 查询医生当前待处理挂号数；
  - 在删除医生时检查与挂号、病历的关联，避免“脏删”。

---

## 2. 数据模型：DOCTORS 表

摘自 `DATABASE_DESIGN.md` 中的设计：

```text
DOCTORS {
    string id PK       "医生编号"
    string name        "姓名"
    string password    "密码"
    string title       "职称"
    string specialty   "专业领域"
    string phone       "电话"
    string department_id FK "所属科室"
}
```

与医生接口紧密相关的其他表：

- `DEPARTMENTS`（科室）
- `APPOINTMENTS`（挂号；用于统计 pending 数量、删除检查）
- `MEDICAL_RECORDS`（病历；用于删除检查）

---

## 3. 接口总览

| 方法 | 路径                           | 描述                                               |
|------|--------------------------------|----------------------------------------------------|
| GET  | `/api/doctors`                 | 获取所有医生信息，并统计每位医生当前待处理挂号数  |
| GET  | `/api/doctors/<doctor_id>`     | 获取指定医生详情（含所属科室名称）                |
| PUT  | `/api/doctors/<doctor_id>`     | 修改医生信息（可改科室、职称、专长、电话、密码）  |
| DELETE | `/api/doctors/<doctor_id>`   | 删除医生；若存在挂号或病历关联则禁止删除          |


---

## 4. 获取医生列表：GET /api/doctors

### 4.1 路由定义

```python
@doctor_bp.route('/api/doctors', methods=['GET'])
def get_doctors():
    ...
```

### 4.2 功能说明

- 从 `DOCTORS` 表查询所有医生基本信息；
- 通过 **子查询** 统计每个医生当前处于 `status = 'pending'` 的挂号数量；
- 按每一行构造包含 `pendingCount` 字段的 JSON 数组返回。

### 4.3 核心 SQL

```sql
SELECT
    d.id,
    d.name,
    d.department_id,
    d.title,
    d.specialty,
    d.phone,
    (
      SELECT COUNT(*)
      FROM appointments a
      WHERE a.doctor_id = d.id
        AND a.status = 'pending'
    ) AS pending_count
FROM doctors d;
```

### 4.4 响应示例

```json
[
  {
    "id": "D001",
    "name": "张医生",
    "departmentId": "DEP001",
    "title": "主任医师",
    "specialty": "心血管内科",
    "phone": "13800000000",
    "pendingCount": 3
  },
  {
    "id": "D002",
    "name": "李医生",
    "departmentId": "DEP002",
    "title": "主治医师",
    "specialty": "呼吸内科",
    "phone": "13800000001",
    "pendingCount": 0
  }
]
```

### 4.5 错误与日志

- 正常流程：
  - `logger.info("Request to get all doctors.")`
  - 查询完成后：`logger.info("Fetched %d doctors with pending counts...", len(data))`
- 异常时：
  - 捕获 `Exception`，记录 `logger.error("Error occurred while fetching doctors: %s", e)`
  - 返回：`500 {"error": "<错误信息>"}`

- 资源释放：
  - 在 `finally` 里关闭 `cursor` / `conn`，并记录 `"Database connection closed."`

---

## 5. 获取医生详情：GET /api/doctors/<doctor_id>

### 5.1 路由定义

```python
@doctor_bp.route('/api/doctors/<doctor_id>', methods=['GET'])
def get_doctor_detail(doctor_id):
    ...
```

### 5.2 功能说明

- 根据 `doctor_id` 查询某个医生的详细信息；
- 通过 `LEFT JOIN departments` 额外返回所属科室名称。

### 5.3 核心 SQL

```sql
SELECT
    d.id,
    d.name,
    d.title,
    d.specialty,
    d.phone,
    d.department_id,
    dept.name AS department_name
FROM doctors d
LEFT JOIN departments dept ON d.department_id = dept.id
WHERE d.id = %s;
```

### 5.4 成功响应示例

```json
{
  "id": "D001",
  "name": "张医生",
  "title": "主任医师",
  "specialty": "心血管内科",
  "phone": "13800000000",
  "departmentId": "DEP001",
  "departmentName": "心内科"
}
```

### 5.5 失败场景

- **医生不存在**

  - 判断 `row is None`：
  - 日志：`logger.warning("Doctor %s not found.", doctor_id)`
  - 返回：`404 {"success": false, "message": "医生不存在"}`

- **其他异常**

  - 日志：`logger.error("Error fetching doctor %s: %s", doctor_id, e)`
  - 返回：`500 {"error": "<错误信息>"}`

- 同样在 `finally` 中关闭数据库连接并记录日志。

---

## 6. 修改医生信息：PUT /api/doctors/<doctor_id>

### 6.1 路由定义

```python
@doctor_bp.route('/api/doctors/<string:doctor_id>', methods=['PUT'])
def update_doctor_detail(doctor_id):
    ...
```

### 6.2 请求体格式

请求体为 JSON，支持部分字段更新：

```json
{
  "name": "新姓名，可选",
  "title": "新职称，可选",
  "specialty": "新专业，可选",
  "phone": "新电话，可选",
  "departmentId": "新科室ID，可选",
  "password": "新密码，可选"
}
```

### 6.3 业务流程

1. **记录请求日志**

   ```python
   logger.info("Request to update doctor %s: %s", doctor_id, data)
   ```

2. **校验科室存在性**

   ```python
   dept_id = data.get('departmentId')
   if dept_id:
       cursor.execute("SELECT id FROM departments WHERE id = %s", (dept_id,))
       if not cursor.fetchone():
           logger.warning("Department %s not found when updating doctor %s.", dept_id, doctor_id)
           return jsonify({"success": False, "message": "所属科室不存在"}), 400
   ```

3. **构造动态 UPDATE 语句**

   - 使用 `fields` 和 `params` 累积需要更新的字段：

   ```python
   fields = []
   params = []
   if 'name' in data:
       fields.append("name = %s"); params.append(data.get('name'))
   if 'title' in data:
       fields.append("title = %s"); params.append(data.get('title'))
   if 'specialty' in data:
       fields.append("specialty = %s"); params.append(data.get('specialty'))
   if 'phone' in data:
       fields.append("phone = %s"); params.append(data.get('phone'))
   if dept_id is not None:
       fields.append("department_id = %s"); params.append(dept_id)
   if 'password' in data:
       fields.append("password = %s"); params.append(data.get('password'))
   ```

4. **无可更新字段时的处理**

   ```python
   if not fields:
       return jsonify({"success": False, "message": "没有提供可更新字段"}), 400
   ```

5. **执行 UPDATE**

   ```python
   sql = "UPDATE doctors SET " + ", ".join(fields) + " WHERE id = %s"
   params.append(doctor_id)
   cursor.execute(sql, tuple(params))
   ```

   - 若 `cursor.rowcount == 0`：
     - 说明医生不存在或已被删除；
     - 回滚事务，返回 `404`。

6. **提交事务**

   - 成功则 `conn.commit()`；
   - 返回：

     ```json
     {
       "success": true,
       "message": "医生信息更新成功"
     }
     ```

### 6.4 错误处理与日志

- 异常时回滚事务：

  ```python
  except Exception as e:
      if conn: conn.rollback()
      logger.error("Error updating doctor %s: %s", doctor_id, str(e))
      return jsonify({"success": False, "message": str(e)}), 500
  ```

- `finally` 中关闭连接并记录：

  ```python
  logger.info("Database connection closed for doctor update.")
  ```

---

## 7. 删除医生：DELETE /api/doctors/<doctor_id>

### 7.1 路由定义

```python
@doctor_bp.route('/api/doctors/<string:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    ...
```

### 7.2 设计目标

删除医生时需要保证：

- 若医生仍然有 **挂号记录**（任意状态），禁止删除；
- 若医生仍然有 **病历记录**，禁止删除；
- 只有完全无关联业务数据时才能物理删除该医生。

### 7.3 详细流程

1. **记录删除请求**

   ```python
   logger.info("Request to delete doctor with ID: %s (simple logic).", doctor_id)
   ```

2. **检查挂号关联**

   ```python
   cursor.execute("SELECT COUNT(*) FROM appointments WHERE doctor_id = %s", (doctor_id,))
   appointment_count = cursor.fetchone()[0]

   if appointment_count > 0:
       logger.warning(
           "Attempt to delete doctor %s failed: Doctor has %d associated appointments (any status).",
           doctor_id, appointment_count
       )
       return jsonify({"success": False,
                       "message": "无法删除：该医生仍有关联的挂号记录。请先处理相关挂号。"}), 400
   ```

   > 注意：这里不区分挂号的状态，只要存在任何记录就不允许删除。

3. **检查病历关联**

   ```python
   cursor.execute("SELECT COUNT(*) FROM medical_records WHERE doctor_id = %s", (doctor_id,))
   record_count = cursor.fetchone()[0]

   if record_count > 0:
       logger.warning(
           "Attempt to delete doctor %s failed: Doctor has %d associated medical records.",
           doctor_id, record_count
       )
       return jsonify({"success": False,
                       "message": "无法删除：该医生仍有关联的病历记录。请先处理相关病历。"}), 400
   ```

4. **执行删除**

   ```python
   cursor.execute("DELETE FROM doctors WHERE id = %s", (doctor_id,))
   if cursor.rowcount == 0:
       conn.rollback()
       logger.warning("Doctor with ID %s not found for deletion.", doctor_id)
       return jsonify({"success": False, "message": "医生不存在或已删除。"}), 404
   ```

5. **提交事务 & 返回成功**

   ```python
   conn.commit()
   logger.info("Doctor with ID %s deleted successfully.", doctor_id)
   return jsonify({"success": True, "message": "医生删除成功。"}), 200
   ```

### 7.4 异常处理

- 任何异常都将触发回滚：

  ```python
  except Exception as e:
      if conn:
          conn.rollback()
      logger.error("Error deleting doctor %s: %s", doctor_id, str(e))
      return jsonify({"success": False, "message": str(e)}), 500
  ```

- 最终关闭连接并记录日志：

  ```python
  logger.info("Database connection closed for doctor deletion.")
  ```

---

## 8. 设计要点

1. **权限控制**
   - 目前模块本身不做权限判断，依赖上层（如 auth / 前端）控制；

2. **软删除支持**
   - 现在是物理删除（`DELETE FROM doctors`）；

3. **分页与筛选**
   - 当前 `GET /api/doctors` 一次性返回全部医生；

---
