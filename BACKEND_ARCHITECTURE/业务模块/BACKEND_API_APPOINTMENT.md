# BACKEND_API_APPOINTMENT.md

> 适用代码版本：`app/api/appointment.py`（来自当前 backend.zip）

---

## 1. 模块概览

- **模块路径**：`app/api/appointment.py`
- **蓝图名称**：`appointment_bp`
- **依赖**：
  - `flask`：`Blueprint`, `request`, `jsonify`
  - `app.utils.db.get_db_connection`：获取 MySQL 连接（连接池）
  - `logging`：记录接口访问与错误日志
  - `collections.defaultdict`：用于统计分组（按小时）
  - `datetime`：处理日期与时间范围

- **主要职责**：
  - 挂号信息查询（按患者、按管理员、按医生/科室、按状态过滤）；
  - 挂号按年/月/日统计（按小时维度聚合）；
  - 新增挂号：
    - 校验患者在同一科室是否已有“待就诊（`pending`）”挂号；
    - 自动为新挂号分配医生（选“当前 pending 数最少”的医生）；
  - 更新挂号状态（如从 `pending` → `finished` / `canceled` 等）。

---

## 2. 相关数据模型

### 2.1 APPOINTMENTS 表（挂号表）

结合源码使用情况，典型结构如下（字段名以实际 SQL 为准）：

```text
APPOINTMENTS {
    string id PK           "挂号编号"
    string patient_id      "患者编号（外键 → PATIENTS.id）"
    string department_id   "科室编号（外键 → DEPARTMENTS.id）"
    string doctor_id       "医生编号（外键 → DOCTORS.id，可为空）"
    string description     "挂号备注/主诉"
    string status          "挂号状态（pending/finished/canceled/...）"
    datetime create_time   "挂号创建时间"
}
```

### 2.2 关联表

- `PATIENTS`：用于查询患者姓名、电话、年龄等；
- `DOCTORS`：用于挂号时自动分配医生、按科室查询挂号；
- `DEPARTMENTS`：用于关联科室信息（科室名称等）。

---

## 3. 接口总览

| 方法   | 路径                                      | 描述                                              |
|--------|-------------------------------------------|---------------------------------------------------|
| GET    | `/api/appointments`                      | 获取挂号数据（按角色/日期/医生/患者过滤）        |
| GET    | `/api/appointments/statistics`           | 按年/月/日统计挂号数据（结果按“小时”分组）       |
| POST   | `/api/appointments`                      | 新增挂号（含重复挂号校验与自动分配医生）         |
| PUT    | `/api/appointments/<string:apt_id>`      | 更新挂号状态                                      |

---

## 4. 获取挂号列表：GET /api/appointments

### 4.1 路由定义

```python
@appointment_bp.route('/api/appointments', methods=['GET'])
def get_appointments():
    ...
```

### 4.2 请求参数（Query String）

- `role`（可选，string）
  - 目前用于区分管理员场景：当 `role=admin` 且传入 `date` 时，查询指定日期所有挂号；
- `date`（可选，string）
  - 与 `role=admin` 搭配使用：`YYYY-MM-DD` 格式，表示某一天；
- `doctor_id`（可选，string）
  - 按医生所在科室查询挂号；
- `patient_id`（可选，string）
  - 按患者查询该患者 **待就诊（`pending`）** 的挂号。

### 4.3 业务逻辑分支

1. **基础 SQL：关联医生和科室**

   ```sql
   SELECT a.id AS appointment_id, a.patient_id, a.department_id, a.doctor_id,
          a.description, a.status, a.create_time,
          d.name   AS doctor_name,
          dept.name AS department_name
   FROM appointments a
   LEFT JOIN doctors d    ON a.doctor_id = d.id
   LEFT JOIN departments dept ON a.department_id = dept.id
   ```

2. **分支逻辑**

   ```python
   role = request.args.get('role')
   date = request.args.get('date')
   doctor_id = request.args.get('doctor_id')
   patient_id = request.args.get('patient_id')
   ```

   - **(1) 按患者查询**：若提供 `patient_id`  
     - 返回该患者 **所有 `status='pending'`** 的挂号记录：

       ```sql
       ... WHERE a.patient_id = %s AND a.status = 'pending'
       ```

   - **(2) 管理员按日期查询**：`role == 'admin'` 且提供 `date`  
     - 返回指定日期的所有挂号记录：

       ```sql
       ... WHERE DATE(a.create_time) = %s
       ```

   - **(3) 按医生所在科室查询**：提供 `doctor_id`  
     - 先根据 `doctor_id` 查询出该医生所属科室 `department_id`：
       ```sql
       SELECT department_id FROM doctors WHERE id = %s
       ```
     - 再查该科室所有挂号：
       ```sql
       ... WHERE a.department_id = %s
       ```
     - 若医生不存在，返回 `404 {"error": "Doctor not found"}`。

   - **(4) 默认情况**：未提供 `patient_id` / `doctor_id` / 合法管理员条件  
     - 返回所有 **未完成挂号**：
       ```sql
       ... WHERE a.status = 'pending'
       ```

3. **结果集后处理：补充患者信息**

   查询挂号表后，对每一条记录再次查询患者信息：

   ```python
   cursor.execute("SELECT name, phone, age FROM patients WHERE id = %s",
                  (row['patient_id'],))
   patient = cursor.fetchone()
   if not patient:
       continue
   ```

### 4.4 返回结果结构

最终构造的数据格式：

```python
data.append({
    "id": row['appointment_id'],
    "patientId": row['patient_id'],
    "patientName": patient['name'],
    "patientPhone": patient['phone'],
    "age": patient['age'],
    "departmentId": row['department_id'],
    "departmentName": row['department_name'],
    "doctorId": row['doctor_id'] if row['doctor_id'] else None,
    "doctorName": row['doctor_name'] if row['doctor_name'] else None,
    "status": row['status'],
    "createTime": row['create_time'],
    "description": row['description']
})
```

返回示例：

```json
[
  {
    "id": "APT001",
    "patientId": "P001",
    "patientName": "张三",
    "patientPhone": "13800000000",
    "age": 28,
    "departmentId": "D001",
    "departmentName": "心内科",
    "doctorId": "DOC001",
    "doctorName": "李医生",
    "status": "pending",
    "createTime": "2024-01-01T09:30:00",
    "description": "胸闷胸痛一周"
  }
]
```

### 4.5 错误处理

- 捕获异常后记录错误日志：
  - `"Error occurred while fetching appointments: %s"`
- 返回：
  - `500 {"error": "<错误信息>"}`

---

## 5. 按年/月/日统计挂号：GET /api/appointments/statistics

### 5.1 路由定义

```python
@appointment_bp.route('/api/appointments/statistics', methods=['GET'])
def get_appointment_statistics():
    ...
```

### 5.2 请求参数（Query String）

- `date`（可选，string）
  - 可支持三种格式：
    - `YYYY-MM-DD`：按“天”统计，取该日 0:00 到次日 0:00；
    - `YYYY-MM`：按“月”统计，该月第一天到下月第一天；
    - `YYYY`：按“年”统计，该年 1 月 1 日到下一年 1 月 1 日；
- `role`（可选，string）
  - 当前代码中接收但未参与进一步逻辑判断（预留扩展）。

### 5.3 时间范围与 SQL 构建

1. **解析 `date` 参数**：

   ```python
   date = request.args.get('date')
   role = request.args.get('role')
   ```

   - 若存在 `date`：
     - 按 `-` 分割：
       - 长度 3 → `year, month, day`
       - 长度 2 → `year, month`
       - 长度 1 → `year`
     - 分别构造 `start_date`、`end_date`：
       - 天：`[当天 0:00, 下一天 0:00)`
       - 月：`[当月 1 号 0:00, 下个月 1 号 0:00)`
       - 年：`[该年 1 月 1 号 0:00, 下一年 1 月 1 号 0:00)`
     - 生成时间条件语句：

       ```python
       time_condition = "WHERE a.create_time >= %s AND a.create_time < %s"
       params = (start_date, end_date)
       ```

     - 无法解析的格式，直接返回：
       - `400 {"error": "Invalid date format"}`

   - 若 **未提供 `date`**：
     - 不加时间过滤，统计所有数据：

       ```python
       time_condition = ""
       params = ()
       ```

2. **执行 SQL**

   ```python
   sql = """
       SELECT a.create_time
       FROM appointments a
       LEFT JOIN doctors d ON a.doctor_id = d.id
       LEFT JOIN departments dept ON a.department_id = dept.id
       {}
   """.format(time_condition)

   cursor.execute(sql, params)
   rows = cursor.fetchall()
   ```

### 5.4 统计逻辑（按小时分组）

- 使用 `defaultdict(int)` 聚合每个小时的数量：

  ```python
  hourly_stats = defaultdict(int)
  for row in rows:
      create_time = row['create_time']
      if isinstance(create_time, str):
          try:
              create_time = datetime.datetime.strptime(
                  create_time, '%Y-%m-%d %H:%M:%S.%f')
          except ValueError:
              create_time = datetime.datetime.strptime(
                  create_time, '%Y-%m-%d %H:%M:%S')

      hour = create_time.hour
      hourly_stats[hour] += 1
  ```

- 构造返回值：

  ```python
  stats = [
      {"hour": hour, "count": count}
      for hour, count in sorted(hourly_stats.items())
  ]
  ```

返回示例：

```json
[
  {"hour": 9,  "count": 12},
  {"hour": 10, "count": 25},
  {"hour": 11, "count": 8}
]
```

---

## 6. 提交挂号：POST /api/appointments

### 6.1 路由定义

```python
@appointment_bp.route('/api/appointments', methods=['POST'])
def create_appointment():
    ...
```

### 6.2 请求体（JSON）

```json
{
  "id": "APT001",
  "patientId": "P001",
  "departmentId": "D001",
  "doctorId": "DOC001",           // 可选；不传则自动分配
  "description": "胸闷胸痛一周",   // 可选
  "createTime": "2024-01-01 09:30:00"
}
```

### 6.3 业务流程

1. **基础准备**

   ```python
   data = request.json
   patient_id = data.get('patientId')
   dept_id = data.get('departmentId')
   ```

   - 记录日志：收到的创建请求。

2. **【高级校验】防止重复挂号**

   需求：**同一患者在同一科室，不能同时有多条状态为 `pending` 的挂号**。

   ```python
   if patient_id:
       check_sql = """
           SELECT COUNT(*) FROM appointments 
           WHERE patient_id = %s AND department_id = %s AND status = 'pending'
       """
       cursor.execute(check_sql, (patient_id, dept_id))
       (existing_count,) = cursor.fetchone()

       if existing_count > 0:
           logger.warning("Patient ID %s already has a pending appointment in department %s",
                          patient_id, dept_id)
           return jsonify({
               "success": False,
               "message": "您在该科室已有待就诊的挂号，请勿重复挂号"
           }), 400
   ```

3. **自动分配医生（负载均衡）**

   若未在请求体中指定 `doctorId`，则自动为该挂号分配医生：

   ```python
   doctor_id = data.get('doctorId')
   if not doctor_id:
       assign_sql = """
           SELECT d.id 
           FROM doctors d
           LEFT JOIN appointments a
               ON d.id = a.doctor_id AND a.status = 'pending'
           WHERE d.department_id = %s
           GROUP BY d.id
           ORDER BY COUNT(a.id) ASC
           LIMIT 1
       """
       cursor.execute(assign_sql, (dept_id,))
       res = cursor.fetchone()
       if res:
           doctor_id = res[0]
           logger.info("Assigned doctor ID %s to the appointment", doctor_id)
       else:
           logger.error("No available doctors in department %s", dept_id)
           return jsonify({
               "success": False,
               "message": "该科室暂无医生排班"
           }), 400
   ```

   - 逻辑说明：
     - 统计每位医生当前 `pending` 状态的挂号数量；
     - 选取挂号数量最少的医生作为分配对象；
     - 若科室中没有任何医生，返回 400 错误。

4. **插入挂号记录**

   ```python
   sql = """
       INSERT INTO appointments
           (id, patient_id, department_id, doctor_id, description, status, create_time)
       VALUES (%s, %s, %s, %s, %s, %s, %s)
   """
   cursor.execute(sql, (
       data.get('id'),
       data.get('patientId'),
       dept_id,
       doctor_id,
       data.get('description', ''),
       'pending',
       data.get('createTime')
   ))

   conn.commit()
   logger.info("Appointment created successfully with ID: %s", data.get('id'))
   return jsonify({
       "success": True,
       "message": f"挂号成功，已分配医生ID: {doctor_id}"
   })
   ```

### 6.4 错误处理与资源释放

- 异常时：
  - `conn.rollback()`；
  - 返回 `500 {"success": False, "message": "<错误信息>"}`；
- 在 `finally` 中关闭连接并记录 `"Database connection closed."`。

---

## 7. 更新挂号状态：PUT /api/appointments/<apt_id>

### 7.1 路由定义

```python
@appointment_bp.route('/api/appointments/<string:apt_id>', methods=['PUT'])
def update_appointment_status(apt_id):
    ...
```

### 7.2 请求体（JSON）

```json
{
  "status": "finished"   // 或 "canceled" 等
}
```

### 7.3 业务流程

1. **获取并记录请求**

   ```python
   data = request.json
   new_status = data.get('status')
   logger.info("Received update request for appointment ID: %s with new status: %s",
               apt_id, new_status)
   ```

2. **更新 SQL**

   ```python
   sql = "UPDATE appointments SET status = %s WHERE id = %s"
   cursor.execute(sql, (data.get('status'), apt_id))
   conn.commit()

   logger.info("Successfully updated appointment ID: %s to status: %s",
               apt_id, new_status)

   return jsonify({"success": True, "message": "挂号状态已更新"})
   ```

3. **异常与资源释放**

   - 异常→回滚、记录错误日志、返回 500；
   - `finally` 中关闭游标与连接，并输出 `"Database connection closed for appointment ID: %s"`。

---

## 8. 小结

挂号模块 `appointment.py` 的几个设计特点：

1. **接口职责清晰**：查询、统计、新增、更新各自独立；
2. **业务约束明确**：
   - 阻止患者在同一科室存在多个 `pending` 挂号；
   - 自动医生分配实现了简单的负载均衡（按 pending 数量）；
3. **统计维度合理**：
   - 按年/月/日筛选后，再按“小时”聚合，便于前端画出高峰时段折线图或柱状图；
4. **错误处理与日志充足**：
   - 所有接口均有 try/except/finally；
   - 关键步骤有 info / warning / error 级别日志。

