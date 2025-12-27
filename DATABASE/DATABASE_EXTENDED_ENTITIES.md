# 数据库设计：扩展实体 (DATABASE_EXTENDED_ENTITIES)

**项目名称**: MedData Hub 医疗数据管理系统  
**数据库名**: `meddata_hub`  

本文件用于描述系统中的 **扩展实体（Extended Entities）**，即与核心业务实体有关联，但主要职责是为其提供“附件 / 文件 / 外部数据扩展”的表结构。

当前系统中的扩展实体为：

- `multimodal_data` —— 多模态数据表，用于关联患者 / 病历与 `uploaded_files/` 文件目录中的各种非结构化或半结构化数据。

> 核心业务实体（`appointments`, `medical_records`）详见：`DATABASE_BUSINESS_ENTITIES.md`  
> 核心主数据实体（`patients`, `doctors`, `departments`, `medicines`）详见：相应的核心实体文档  
> 关联实体（`prescription_details`）详见：`DATABASE_RELATION_ENTITIES.md`

---

# 1. 多模态扩展实体 `multimodal_data`

## 1.1 业务含义

`multimodal_data` 用于统一管理系统中的 **多模态医疗数据**，包括但不限于：

- 文档类：入院记录、出院小结、治疗方案等 PDF（`Document` / `MedicalRecord`）
- 医学影像：CT、MRI、超声等图片（`MedicalImage`）
- 音频：心理咨询录音、术后交代录音等（`AudioRecord`）
- 视频：标准操作视频、教学视频（`StandardVideo`）
- 基因数据：FASTA 文件、分析结果图片（`GenomicData`）
- 设备数据：监护仪/设备导出的 PDF 报告（`DeviceData`）
- 时间序列：血压、血糖、体温等监测 CSV（`patient_blood_*`, `patient_temperature`）

它的主要职责是：

1. 作为 **结构化医疗实体（患者/病历）** 与 **文件系统（uploaded_files/）** 之间的桥接层；  
2. 为各类非结构化文件提供统一的索引、查询与扩展能力；  
3. 支撑后续多模态分析、可视化以及 AI 模型的数据输入。

---

## 1.2 表结构（DDL）

> 以下结构基于当前 SQL 文件与插入脚本（如 `insert_multimodal.py`）的设计。

```sql
CREATE TABLE `meddata_hub`.`multimodal_data` (
    `id` VARCHAR(50) PRIMARY KEY,          -- 多模态记录的 ID，如 'doc_1', 'img_1'
    `patient_id` VARCHAR(50) NULL,         -- 关联患者，可为空
    `record_id` VARCHAR(50) NULL,          -- 关联病历，可为空
    `source_table` VARCHAR(100) NOT NULL,  -- 逻辑来源类型：Document / MedicalImage / AudioRecord / StandardVideo / GenomicData / DeviceData / BloodPressureCSV 等
    `source_pk` VARCHAR(50) NOT NULL,      -- 来源内部的“主键”或标识，例如 AdmissionRecord1 / CTImage1
    `modality` ENUM('text','image','audio','video','pdf','timeseries','other') NOT NULL, -- 模态类型
    `text_content` LONGTEXT NULL,          -- 纯文本内容（若适用，如基因序列文本/TXT 内容）
    `file_path` VARCHAR(255) NULL,         -- 文件相对路径，如 'uploaded_files/medicaldata/Document/AdmissionRecord1.pdf'
    `file_format` VARCHAR(20) NULL,        -- 文件格式：pdf / jpg / mp3 / mp4 / csv / fasta 等
    `description` TEXT NULL,               -- 简要说明
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_patient` (`patient_id`),
    INDEX `idx_modality` (`modality`)
);

-- 外键关联 patients 表
ALTER TABLE `meddata_hub`.`multimodal_data`
ADD CONSTRAINT `fk_multimodal_patient`
    FOREIGN KEY (`patient_id`)
    REFERENCES `meddata_hub`.`patients` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

-- 外键关联 medical_records 表
ALTER TABLE `meddata_hub`.`multimodal_data`
ADD CONSTRAINT `fk_multimodal_record`
    FOREIGN KEY (`record_id`)
    REFERENCES `meddata_hub`.`medical_records` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE;
```

---

## 1.3 字段说明

| 字段名       | 类型                                                | 约束               | 说明 |
|--------------|-----------------------------------------------------|--------------------|------|
| id           | VARCHAR(50)                                        | PK, NOT NULL       | 多模态记录唯一 ID，如 `doc_1`、`img_ct_1` |
| patient_id   | VARCHAR(50)                                        | FK，可为 NULL      | 关联患者 ID，对应 `patients.id` |
| record_id    | VARCHAR(50)                                        | FK，可为 NULL      | 关联病历 ID，对应 `medical_records.id` |
| source_table | VARCHAR(100)                                       | NOT NULL           | 逻辑来源类型，如 `Document`、`MedicalImage`、`AudioRecord`、`StandardVideo`、`GenomicData`、`DeviceData`、`BloodPressureCSV` 等 |
| source_pk    | VARCHAR(50)                                        | NOT NULL           | 来源内部标识，如 `AdmissionRecord1`、`CTImage1`、`patient_blood_pressure1` |
| modality     | ENUM('text','image','audio','video','pdf','timeseries','other') | NOT NULL | 模态类型：文本、图片、音频、视频、PDF、时间序列等 |
| text_content | LONGTEXT                                           | 可为 NULL          | 文本内容（如 OCR 结果、FASTA 序列等），非文本文件可留空 |
| file_path    | VARCHAR(255)                                       | 可为 NULL          | 文件相对路径，如 `uploaded_files/medicaldata/Document/AdmissionRecord1.pdf` |
| file_format  | VARCHAR(20)                                        | 可为 NULL          | 文件格式/后缀，如 `pdf`、`jpg`、`mp3`、`mp4`、`csv`、`fasta` |
| description  | TEXT                                               | 可为 NULL          | 人类可读的说明，如“示例 CT 影像”“患者 1 血压监测数据” |
| created_at   | DATETIME                                           | 默认当前时间       | 创建时间戳 |

---

## 1.4 与核心/业务实体的关系

### （1）与 `patients`（患者）

- 关系：1（患者） : N（多模态记录）
- 外键：`fk_multimodal_patient`
- 约束策略：`ON DELETE SET NULL`
  - 当某个患者记录被删除时，多模态记录仍保留，只是 `patient_id` 置空；

### （2）与 `medical_records`（病历）

- 关系：1（病历） : N（多模态记录）
- 外键：`fk_multimodal_record`
- 约束策略：`ON DELETE SET NULL`
  - 删除病历时不强制删除多模态记录；


---

## 1.5 与 `uploaded_files/` 目录结构的映射

当前项目中 `uploaded_files/` 目录结构（节选）如下：

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

与 `multimodal_data` 中字段的典型映射方式如下：

1. **医疗文档（Document / MedicalRecord）**

   - 目录：
     - `uploaded_files/medicaldata/Document/AdmissionRecord1.pdf`
     - `uploaded_files/medicaldata/MedicalRecord/DiagnosisResult1.pdf` 等
   - 示例记录：
     - `source_table = 'Document'` 或 `'MedicalRecord'`
     - `source_pk = 'AdmissionRecord1'`
     - `modality = 'pdf'`
     - `file_format = 'pdf'`
     - `file_path = 'uploaded_files/medicaldata/Document/AdmissionRecord1.pdf'`

2. **医学影像（MedicalImage）**

   - 目录：
     - `uploaded_files/medicaldata/MedicalImage/CTImage1.jpg`
     - `uploaded_files/medicaldata/MedicalImage/MRIImage1.bmp`
     - `uploaded_files/medicaldata/MedicalImage/UltrasoundImage1.png`
   - 示例：
     - `source_table = 'MedicalImage'`
     - `source_pk = 'CTImage1'`
     - `modality = 'image'`
     - `file_format = 'jpg'` / `bmp` / `png`

3. **音频（AudioRecord）**

   - 目录：
     - `uploaded_files/medicaldata/AudioRecord/心理咨询录音.mp3`
     - `uploaded_files/medicaldata/AudioRecord/术后护理录音.mp3`
   - 示例：
     - `source_table = 'AudioRecord'`
     - `modality = 'audio'`
     - `file_format = 'mp3'`

4. **视频（StandardVideo）**

   - 目录：
     - `uploaded_files/medicaldata/StandardVideo/应急处理标准视频.mp4`
     - `uploaded_files/medicaldata/StandardVideo/手术流程视频.mp4`
   - 示例：
     - `source_table = 'StandardVideo'`
     - `modality = 'video'`
     - `file_format = 'mp4'`

5. **基因数据（GenomicData）**

   - 目录：
     - `uploaded_files/medicaldata/GenomicData/GeneSequence1.fasta`
     - `uploaded_files/medicaldata/GenomicData/AnalysisResult1.jpeg`
   - 示例：
     - 基因序列：
       - `source_table = 'GenomicData'`
       - `modality = 'text'` 或 `'other'`
       - `file_format = 'fasta'`
     - 分析结果图片：
       - `modality = 'image'`
       - `file_format = 'jpeg'`

6. **设备 PDF（DeviceData）**

   - 目录：
     - `uploaded_files/medicaldata/DeviceData/DataContent1.pdf`
   - 示例：
     - `source_table = 'DeviceData'`
     - `modality = 'pdf'`
     - `file_format = 'pdf'`

7. **时间序列 CSV（血压/血糖/体温）**

   - 目录：
     - `uploaded_files/patient_blood_pressure/patient_blood_pressure1.csv`
     - `uploaded_files/patient_blood_sugar/patient_blood_sugar1.csv1.csv`
     - `uploaded_files/patient_temperature/patient_temperature1.csv`
   - 示例：
     - `source_table = 'BloodPressureCSV' / 'BloodSugarCSV' / 'TemperatureCSV'`
     - `modality = 'timeseries'`
     - `file_format = 'csv'`

---

## 1.6 典型业务用法

1. **挂载附件到病历**

   - 病历创建后，将相关文件（PDF、影像、音频等）上传至 `uploaded_files/`；
   - 为每个文件插入一条 `multimodal_data` 记录：
     - 设置 `record_id = <病历ID>`
     - 可选设置 `patient_id`、`description` 等；
   - 前端在病历详情页中通过 `record_id` 查询并展示所有多模态附件。

2. **查看某患者的全部多模态历史**

   - 根据 `patient_id` 查询 `multimodal_data`，按 `created_at` 逆序排序；
   - 可用于：
     - 总览某患者所有影像、报告、监测数据；
     - 为多模态 AI 模型准备输入样本。

3. **模态分布与统计**

   - 用于统计不同模态数据的数量/占比：
     - 例如：image/audio/video/pdf/timeseries 各占比多少；
   - 可为仪表盘、Sankey 图、流向分析提供数据源。

---

## 1.7 常用查询示例

1. **获取某条病历的所有附件**

```sql
SELECT *
FROM multimodal_data
WHERE record_id = :record_id
ORDER BY created_at DESC;
```

2. **获取某患者的所有多模态数据**

```sql
SELECT *
FROM multimodal_data
WHERE patient_id = :patient_id
ORDER BY created_at DESC;
```

3. **按模态类型统计数量**

```sql
SELECT modality, COUNT(*) AS cnt
FROM multimodal_data
GROUP BY modality;
```

4. **按来源类型统计数量**

```sql
SELECT source_table, COUNT(*) AS cnt
FROM multimodal_data
GROUP BY source_table;
```


# 2. 扩展实体设计总结

`multimodal_data` 作为扩展实体，其核心定位是：

- 不直接代表某一“临床事件”（不像挂号/病历）  
- 也不是传统意义的多对多桥表（不像处方明细）  
- 而是为 **患者** 与 **病历** 提供一个“外挂式”的多模态附件层

它将 `uploaded_files/` 中复杂的目录与文件组织统一抽象为结构化表数据，为后续：

- 临床应用  
- 多模态 AI  
- 可视化与大屏展示  

提供了稳定的数据入口与检索接口。



