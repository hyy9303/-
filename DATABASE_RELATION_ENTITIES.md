# 数据库设计：关联实体 (DATABASE_RELATION_ENTITIES)

**项目名称**: MedData Hub 医疗数据管理系统  
**数据库名**: `meddata_hub`

本文件描述系统中的 **关联实体 (Relation / Bridge Entities)**，用于连接多个核心实体或为业务实体提供“明细层”。

当前数据库中主要的关联实体：

- `prescription_details` — 处方明细（连接 `medical_records` 与 `medicines`）
- `multimodal_data` — 多模态数据关联（连接 `patients` / `medical_records` 与文件系统）

> 说明：  
> - 业务实体（如 `appointments`, `medical_records`）已在 `DATABASE_BUSINESS_ENTITIES.md` 中说明。  
> - 核心实体（如 `patients`, `doctors`, `departments`, `medicines`）可在另一份“主数据/核心实体”文档中描述。

---

# 1. 处方明细关联实体 `prescription_details`

## 1.1 业务含义

`prescription_details` 是连接 **病历 (`medical_records`)** 与 **药品 (`medicines`)** 的关联表：

- 一条病历可以对应多条用药明细；
- 同一种药品可以出现在多条病历中。

它既承担 **多对多关联表** 的角色，又承担 **处方行项目 (line item)** 的角色，是医嘱/处方的“明细层”。

---

## 1.2 表结构（DDL）

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

ALTER TABLE `meddata_hub`.`prescription_details` 
ADD CONSTRAINT `fk_detail_record`
  FOREIGN KEY (`record_id`)
  REFERENCES `meddata_hub`.`medical_records` (`id`)
  ON DELETE CASCADE, -- 删除病历时，自动删除处方详情
ADD CONSTRAINT `fk_detail_medicine`
  FOREIGN KEY (`medicine_id`)
  REFERENCES `meddata_hub`.`medicines` (`id`);
```

---

## 1.3 字段说明

| 字段名      | 类型         | 说明 |
|-------------|--------------|------|
| id          | VARCHAR(50)  | 明细唯一 ID（单独一行用药记录） |
| record_id   | VARCHAR(50)  | 所属病历 ID，对应 `medical_records.id` |
| medicine_id | VARCHAR(50)  | 药品 ID，对应 `medicines.id` |
| dosage      | VARCHAR(100) | 单次剂量，如“1 片”“5ml” |
| usage_info  | VARCHAR(100) | 用法说明，如“一日三次，饭后服用” |
| days        | INT          | 用药天数，如 `7` 表示 7 天疗程 |

---

## 1.4 关联关系与约束

- 与 `medical_records`：
  - 关系：一对多（1 条病历 → N 条处方明细）
  - 外键：`fk_detail_record`
  - `ON DELETE CASCADE`：
    - 删除一条病历时，会自动删除其下所有处方明细。
- 与 `medicines`：
  - 关系：多对一（N 条处方明细 → 1 个药品）
  - 外键：`fk_detail_medicine`
  - 无级联删除：通常不允许直接删除仍在处方中使用的药品记录。

> 说明：从关系建模角度看，`prescription_details` 将  
> **medical_records（就诊行为）** 与 **medicines（药品主数据）** 建立了多对多的桥接关系。

---

## 1.5 典型业务用法

- 在接口 `record.py` 中：
  - 创建病历时，前端提交：
    - 病历主信息：`diagnosis`, `treatment_plan` 等；
    - 多条用药明细：`medicine_id + dosage + usage_info + days`。
  - 后端在一个事务中：
    1. 插入 `medical_records`；
    2. 批量插入对应的 `prescription_details`；
    3. 根据用量扣减 `medicines.stock` 库存。
- 在查询病历详情时：
  - 通过 `record_id` 关联查询该病历下所有用药记录。

---

## 1.6 常用查询示例

1. **查询某条病历的全部处方明细：**

```sql
SELECT d.*, m.name AS medicine_name, m.specification
FROM prescription_details d
JOIN medicines m ON d.medicine_id = m.id
WHERE d.record_id = :record_id;
```

2. **统计某个药品被开具的次数：**

```sql
SELECT COUNT(*) AS usage_count
FROM prescription_details
WHERE medicine_id = :medicine_id;
```

---

# 2. 多模态数据关联实体 `multimodal_data`

## 2.1 业务含义

`multimodal_data` 是连接 **病人/病历** 与 **文件系统中多模态文件** 的关联实体：

- 一条记录代表一个“多模态对象”（如一份 PDF、一次影像、一段录音、一个 CSV 等）；
- 通过 `patient_id` / `record_id` 与对应患者、病历关联；
- 通过 `file_path` / `source_table` / `source_pk` 与 `uploaded_files/` 目录中的实际文件对应。

它起到的作用是：

- 为所有非结构化/半结构化数据提供统一索引；
- 将“医疗实体”与“文件”解耦，方便扩展与管理。

---

## 2.2 表结构（DDL）

> 以下为当前 SQL 中定义的结构（包含部分行内注释）：

```sql
CREATE TABLE `meddata_hub`.`multimodal_data` (
    `id` VARCHAR(50) PRIMARY KEY,          -- 多模态记录的 ID，如 'img_1'
    `patient_id` VARCHAR(50) NULL,         -- 预留，之后可以填 patients.id
    `record_id` VARCHAR(50) NULL,         -- 预留，之后可以填 medical_records.id
    `source_table` VARCHAR(100) NOT NULL,  -- 来源类型：Document / MedicalImage / AudioRecord 等
    `source_pk` VARCHAR(50) NOT NULL,     -- 来源里的“主键”或标识，例如 AdmissionRecord1
    `modality` ENUM('text','image','audio','video','pdf','timeseries','other') NOT NULL, -- 文件类型
    `text_content` LONGTEXT NULL,          -- 纯文本内容（如果是 text 模态）
    `file_path` VARCHAR(255) NULL,         -- 文件相对路径，如 medicaldata/Document/AdmissionRecord1.pdf
    `file_format` VARCHAR(20) NULL,        -- 文件格式：pdf / jpg / mp3 / mp4 / csv 等
    `description` TEXT NULL,               -- 描述信息
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_patient` (`patient_id`),    -- 索引：病人的 ID
    INDEX `idx_modality` (`modality`)     -- 索引：文件类型
    );

-- 外键关联 patients 表
ALTER TABLE `meddata_hub`.`multimodal_data`
ADD CONSTRAINT `fk_multimodal_patient`
    FOREIGN KEY (`patient_id`)
    REFERENCES `meddata_hub`.`patients` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- 外键关联 medical_records 表
ALTER TABLE `meddata_hub`.`multimodal_data`
ADD CONSTRAINT `fk_multimodal_record`
    FOREIGN KEY (`record_id`)
    REFERENCES `meddata_hub`.`medical_records` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;
```

---

## 2.3 字段说明

| 字段名       | 类型                                                | 说明 |
|--------------|-----------------------------------------------------|------|
| id           | VARCHAR(50)                                        | 多模态数据唯一 ID，如 `doc_1`, `img_1` |
| patient_id   | VARCHAR(50), 可 NULL                               | 关联患者 ID，对应 `patients.id` |
| record_id    | VARCHAR(50), 可 NULL                               | 关联病历 ID，对应 `medical_records.id` |
| source_table | VARCHAR(100)                                       | 逻辑来源类别，如 `Document` / `MedicalImage` / `AudioRecord` / `StandardVideo` / `GenomicData` / `DeviceData` / `BloodPressureCSV` 等 |
| source_pk    | VARCHAR(50)                                        | 来源内部的“主键”或标识，如 `AdmissionRecord1`、`CTImage1` |
| modality     | ENUM('text','image','audio','video','pdf','timeseries','other') | 模态类型，统一归类文件种类 |
| text_content | LONGTEXT, 可 NULL                                  | 文本类内容或解析结果（如 OCR、基因序列文本等） |
| file_path    | VARCHAR(255), 可 NULL                              | 相对文件路径，对应 `uploaded_files/` 子目录结构 |
| file_format  | VARCHAR(20), 可 NULL                               | 文件格式/扩展名：`pdf` / `jpg` / `mp3` / `mp4` / `csv` / `fasta` 等 |
| description  | TEXT, 可 NULL                                      | 对该多模态记录的人类可读说明 |
| created_at   | DATETIME，默认 `CURRENT_TIMESTAMP`                 | 记录创建时间 |

---

## 2.4 与核心/业务实体的关系

- 与 `patients`：
  - 关系：一对多（1 个患者 → 多条多模态记录）
  - 外键：`fk_multimodal_patient`
  - `ON DELETE SET NULL`：
    - 若患者被删除，相关记录的 `patient_id` 置空，但文件索引仍保留（一般用于测试环境或匿名化处理）。
- 与 `medical_records`：
  - 关系：一对多（1 条病历 → 多个多模态文件）
  - 外键：`fk_multimodal_record`
  - `ON DELETE SET NULL`：
    - 若病历被删除，相关记录的 `record_id` 置空，但多模态记录仍可按患者维度查询。

> 从建模角度看，`multimodal_data` 是连接 **结构化医疗实体**（患者/病历）与 **非结构化文件** 的桥接实体。

---

## 2.5 与文件系统 `uploaded_files/` 的映射

项目中存在以下文件目录结构（节选）：

```text
uploaded_files/
├─ medicaldata
│  ├─ AudioRecord
│  ├─ DeviceData
│  ├─ Document
│  ├─ GenomicData
│  ├─ MedicalImage
│  ├─ MedicalRecord
│  └─ StandardVideo
├─ patient_blood_pressure
├─ patient_blood_sugar
└─ patient_temperature
```

典型映射关系如下：

- `uploaded_files/medicaldata/Document/AdmissionRecord1.pdf`  
  - `source_table = 'Document'`  
  - `source_pk = 'AdmissionRecord1'`  
  - `modality = 'pdf'`  
  - `file_path = 'uploaded_files/medicaldata/Document/AdmissionRecord1.pdf'`
- `uploaded_files/medicaldata/MedicalImage/CTImage1.jpg`  
  - `source_table = 'MedicalImage'`  
  - `source_pk = 'CTImage1'`  
  - `modality = 'image'`
- `uploaded_files/medicaldata/AudioRecord/心理咨询录音.mp3`  
  - `source_table = 'AudioRecord'`  
  - `modality = 'audio'`
- `uploaded_files/patient_blood_pressure/patient_blood_pressure1.csv`  
  - `source_table = 'BloodPressureCSV'`（逻辑类别）  
  - `modality = 'timeseries'`  
  - `file_format = 'csv'`

---

## 2.6 典型业务用法

- 在 `multimodal.py` 中：
  - 上传文件后，写入一条 `multimodal_data` 记录；
  - 根据 `patient_id` / `record_id` 查询该患者/该次就诊关联的所有文件；
  - 前端通过返回的 `file_path` 拼成下载/预览 URL。
- 在 `record.py` 中：
  - 创建病历后，可将相关影像/报告挂接到该病历（设置 `record_id`）。
- 在 `stats.py` 中（可扩展）：
  - 统计某类模态的数量，如各类影像数量占比；
  - 分析某种检查或报告在不同科室/疾病中的使用情况。

---

## 2.7 常用查询示例

1. **按病历获取所有附件：**

```sql
SELECT *
FROM multimodal_data
WHERE record_id = :record_id
ORDER BY created_at DESC;
```

2. **按患者获取所有多模态数据：**

```sql
SELECT *
FROM multimodal_data
WHERE patient_id = :patient_id
ORDER BY created_at DESC;
```

3. **按模态类型统计数量：**

```sql
SELECT modality, COUNT(*) AS cnt
FROM multimodal_data
GROUP BY modality;
```

---

# 3. 关联实体设计小结

本项目中，关联实体主要承担两类职责：

1. **业务明细桥接 (prescription_details)**  
   - 连接“病历”与“药品”，提供处方行项目，实现多对多关系与用药细节记录。

2. **多模态文件桥接 (multimodal_data)**  
   - 连接“医疗实体（患者/病历）”与“文件系统中的多模态数据”，形成统一的索引与管理层。

这两类关联实体与业务实体、核心实体一起，共同构成：

- 完整的诊疗链路：挂号 → 病历 → 处方 → 多模态附件；
- 为统计分析、可视化和下游 AI/多模态分析提供结构化的数据基础。



