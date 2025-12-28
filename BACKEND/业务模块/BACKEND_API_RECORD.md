# BACKEND_API_RECORD.md

> 说明：本文件基于仓库中的 **API_DOCUMENTATION.md** 与 **meddata_hub.sql**，对病历与处方模块的设计做“接口级”说明。

---

## 1. 模块概览

- **模块路径**：`app/api/record.py`
- **蓝图名称**：`record_bp`
- **依赖模块**
  - `flask`：`Blueprint`, `request`, `jsonify`
  - `app.utils.db.get_db_connection`：获取 MySQL 连接（连接池）
  - `app.utils.common.format_date`：日期格式化
  - `logging`：日志记录
  - `datetime.date`：日期处理（如就诊时间）

- **业务职责**
  - 管理病历主表 **medical_records**
  - 管理处方明细表 **prescription_details**
  - 保证写入病历与处方时的 **事务一致性**
  - 在开具处方时对 **药品库存进行校验与扣减**
  - 删除病历时级联删除处方明细（依赖数据库外键）

---

## 2. 相关数据模型

### 2.1 MEDICAL_RECORDS（病历表）

摘自 `meddata_hub.sql`：

```sql
CREATE TABLE `meddata_hub`.`medical_records` (
  `id` VARCHAR(50) NOT NULL,
  `patient_id` VARCHAR(50) NOT NULL,
  `doctor_id` VARCHAR(50) NOT NULL,
  `diagnosis` TEXT(1024) NOT NULL,
  `treatment_plan` TEXT(1024) NOT NULL,
  `visit_date` DATE NOT NULL,
  PRIMARY KEY (`id`)
);
```

外键约束（与患者 & 医生）：

```sql
ALTER TABLE `meddata_hub`.`medical_records` 
ADD CONSTRAINT `fk_record_patient`
  FOREIGN KEY (`patient_id`) REFERENCES `meddata_hub`.`patients` (`id`),
ADD CONSTRAINT `fk_record_doctor`
  FOREIGN KEY (`doctor_id`) REFERENCES `meddata_hub`.`doctors` (`id`);
```

### 2.2 PRESCRIPTION_DETAILS（处方明细表）

```sql
CREATE TABLE `meddata_hub`.`prescription_details` (
  `id` VARCHAR(50) NOT NULL,
  `record_id` VARCHAR(50) NOT NULL,
  `medicine_id` VARCHAR(50) NOT NULL,
  `dosage` VARCHAR(100) NOT NULL,
  `usage_info` VARCHAR(100) NOT NULL,
  `days` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
);
```

与病历、药品表的外键关系：

```sql
ALTER TABLE `meddata_hub`.`prescription_details` 
ADD CONSTRAINT `fk_detail_record`
  FOREIGN KEY (`record_id`)
  REFERENCES `meddata_hub`.`medical_records` (`id`)
  ON DELETE CASCADE,
ADD CONSTRAINT `fk_detail_medicine`
  FOREIGN KEY (`medicine_id`)
  REFERENCES `meddata_hub`.`medicines` (`id`);
```

> 说明：删除病历记录时，对应的处方明细会被 **自动级联删除**。

---

## 3. 接口总览

根据 `API_DOCUMENTATION.md`，`record.py` 模块对外提供的接口如下：

| 方法   | 路径                               | 描述                                                                 |
|--------|------------------------------------|----------------------------------------------------------------------|
| GET    | `/api/records`                     | 获取所有（或某个患者）的病历记录                                     |
| GET    | `/api/prescription_details`        | 获取所有（或某个病历）的处方明细                                     |
| POST   | `/api/records`                     | 提交病历（同时插入病历主表与处方子表，涉及事务处理与库存校验）       |
| DELETE | `/api/records/<record_id>`         | 删除病历（依赖外键自动级联删除对应的处方明细）                       |

---

## 4. 获取病历：GET /api/records

### 4.1 路由定义

```python
@record_bp.route('/api/records', methods=['GET'])
def get_records():
    ...
```

### 4.2 请求参数（Query）

可支持如下查询参数：

- `patientId`：按患者 ID 过滤病历；
- `doctorId`：按医生 ID 过滤；
- `startDate` / `endDate`（可选）：按就诊时间范围过滤；
- `limit` / `offset`（可选）：分页。

示例：

```http
GET /api/records?patientId=P001&limit=20&offset=0
```

### 4.3 典型实现逻辑

1. 建立数据库连接，开启游标（`dictionary=True`）。
2. 基于参数拼接 SQL：
   ```sql
   SELECT
       mr.id,
       mr.patient_id,
       mr.doctor_id,
       mr.diagnosis,
       mr.treatment_plan,
       mr.visit_date,
       p.name AS patient_name,
       d.name AS doctor_name
   FROM medical_records mr
   LEFT JOIN patients p ON mr.patient_id = p.id
   LEFT JOIN doctors  d ON mr.doctor_id = d.id
   WHERE 1 = 1
     [AND mr.patient_id = %s]
     [AND mr.doctor_id  = %s]
     [AND mr.visit_date >= %s]
     [AND mr.visit_date <= %s]
   ORDER BY mr.visit_date DESC
   [LIMIT %s OFFSET %s];
   ```
3. 将日期字段通过 `format_date` 格式化。
4. 构造返回 JSON：

   ```json
   [
     {
       "id": "R001",
       "patientId": "P001",
       "patientName": "张三",
       "doctorId": "D001",
       "doctorName": "李医生",
       "diagnosis": "上呼吸道感染",
       "treatmentPlan": "口服抗生素 + 多喝水休息",
       "visitDate": "2024-01-02"
     }
   ]
   ```

5. 出错时记录日志并返回 500，最终关闭连接与游标。

---

## 5. 获取处方明细：GET /api/prescription_details

### 5.1 路由定义

```python
@record_bp.route('/api/prescription_details', methods=['GET'])
def get_prescription_details():
    ...
```

### 5.2 典型请求参数

- `recordId`：按病历 ID 过滤处方明细；
- `patientId`：可通过 join medical_records 实现“按患者查处方”。

示例：

```http
GET /api/prescription_details?recordId=R001
```

### 5.3 典型实现逻辑

1. 创建连接 / 游标。
2. 组合 SQL（示例）：

   ```sql
   SELECT
       pd.id,
       pd.record_id,
       pd.medicine_id,
       m.name       AS medicine_name,
       m.price      AS unit_price,
       pd.dosage,
       pd.usage_info,
       pd.days
   FROM prescription_details pd
   LEFT JOIN medicines m ON pd.medicine_id = m.id
   [JOIN medical_records mr ON pd.record_id = mr.id]
   WHERE 1 = 1
     [AND pd.record_id = %s]
     [AND mr.patient_id = %s];
   ```

3. 映射为前端友好的结构，例如：

   ```json
   [
     {
       "id": "PD001",
       "recordId": "R001",
       "medicineId": "M001",
       "medicineName": "阿莫西林胶囊",
       "dosage": "0.5g",
       "usageInfo": "口服，每日3次",
       "days": 7,
       "unitPrice": 2.5
     }
   ]
   ```

4. 错误处理与资源释放同上。

---

## 6. 提交病历：POST /api/records

### 6.1 路由定义

```python
@record_bp.route('/api/records', methods=['POST'])
def create_record():
    ...
```

### 6.2 请求体

```json
{
  "record": {
    "id": "R001",
    "patientId": "P001",
    "doctorId": "D001",
    "diagnosis": "上呼吸道感染",
    "treatmentPlan": "口服抗生素 + 多喝水休息",
    "visitDate": "2024-01-02"
  },
  "prescriptions": [
    {
      "medicineId": "M001",
      "dosage": "0.5g",
      "usageInfo": "口服，每日3次",
      "days": 7
    },
    {
      "medicineId": "M002",
      "dosage": "10ml",
      "usageInfo": "口服，每日2次",
      "days": 5
    }
  ]
}
```


### 6.3 事务 & 业务规则

**核心要求**：

- “包含主表和子表插入，事务处理，库存校验”。

典型实现步骤：

1. **开启事务**

   ```python
   conn = get_db_connection()
   cursor = conn.cursor(dictionary=True)
   conn.start_transaction()
   ```

2. **写入病历主表**

   ```sql
   INSERT INTO medical_records
       (id, patient_id, doctor_id, diagnosis, treatment_plan, visit_date)
   VALUES (%s, %s, %s, %s, %s, %s);
   ```

3. **遍历处方明细，做库存校验与插入**

   对于每一条处方：

   1. 校验药品存在 & 库存是否足够：

      ```sql
      SELECT stock FROM medicines WHERE id = %s FOR UPDATE;
      ```

      - 若查询不到此药品 → 返回错误 `"药品不存在"`；
      - 若库存不足 → 返回错误 `"药品库存不足"` 并回滚事务。

   2. 插入处方明细：

      ```sql
      INSERT INTO prescription_details
          (id, record_id, medicine_id, dosage, usage_info, days)
      VALUES (%s, %s, %s, %s, %s, %s);
      ```

   3. 扣减库存：

      ```sql
      UPDATE medicines
      SET stock = stock - %s
      WHERE id = %s;
      ```


4. **提交事务**

   所有校验和写入成功后：

   ```python
   conn.commit()
   return jsonify({"success": True, "message": "病历及处方保存成功"})
   ```

5. **异常处理**

   - 捕获任何异常 → `conn.rollback()`；
   - 记录错误日志；
   - 返回 `500 {"success": False, "message": "<错误信息>"}`。

6. **资源释放**

   在 `finally` 中关闭 `cursor` / `conn`，并记录关闭日志。

---

## 7. 删除病历：DELETE /api/records/<record_id>

### 7.1 路由定义

```python
@record_bp.route('/api/records/<string:record_id>', methods=['DELETE'])
def delete_record(record_id):
    ...
```

### 7.2 业务含义

- 删除单条病历记录；
- 依赖数据库外键上的 `ON DELETE CASCADE`，自动删除该病历下所有处方明细。

### 7.3 典型实现逻辑

1. 创建连接 / 游标，开启事务。
2. 删除病历：

   ```sql
   DELETE FROM medical_records WHERE id = %s;
   ```

3. 判断是否存在记录被删除：

   ```python
   if cursor.rowcount == 0:
       conn.rollback()
       return jsonify({"success": False, "message": "病历不存在或已删除"}), 404
   ```

4. 提交事务：

   ```python
   conn.commit()
   return jsonify({"success": True, "message": "病历及其处方明细删除成功"}), 200
   ```

5. 异常时回滚并返回 500；最后关闭连接。


---

## 8. 日志与错误处理约定

在 `record.py` 中建议遵循统一模式（与其他模块保持一致）：

- 日志等级：
  - `info`：接口入口、关键业务动作（新增病历、删除病历、库存扣减等）；
  - `warning`：业务性异常（记录不存在、库存不足）；
  - `error`：程序异常、数据库异常。
- 错误返回：
  - 业务错误（如库存不够、ID 不存在） → 4xx（通常 400/404），携带 `success=false` 与具体 message；
  - 系统错误 → 500，携带 `success=false` 与错误 message。
- 资源释放：
  - 所有接口在 `finally` 中关闭 `cursor` / `conn`，避免连接泄漏。

---

## 9. 与其它模块的关系

- **与患者模块 (`patient.py`)**
  - 通过 `medical_records.patient_id` 关联；
  - 删除患者时，会先删除患者关联的病历（从而级联删除处方）。

- **与医生模块 (`doctor.py`)**
  - 通过 `medical_records.doctor_id` 关联，统计医生的诊疗记录等。

- **与药品模块 (`basic.py` 中的 medicines)**  
  - 通过 `prescription_details.medicine_id` 关联；
  - 创建病历时需要读取并修改 `medicines.stock`。

- **与多模态模块 (`multimodal.py`)**
  - 多模态数据表 `multimodal_data.record_id` 可指向某一病历；
  - 可在前端实现“查看病历详情时，同时展示相关影像/文档/音频”等多模态信息。

---
