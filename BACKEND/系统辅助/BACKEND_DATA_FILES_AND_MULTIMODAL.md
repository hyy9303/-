# **BACKEND_DATA_FILES_AND_MULTIMODAL.md**  

本说明文档用于详细描述系统中的 **多模态医疗数据（medical images / audio / video / genomic / documents 等）** 与 **本地文件目录结构**、**数据库结构**、**后端 API 模块**之间的关系。

该模块与以下组件强相关：

- `uploaded_files/`（实体文件存储根目录）
- `app/api/multimodal.py`（多模态 API 接口）
- `insert_data_python/insert_multimodal.py`（自动插入多模态数据）
- `DATABASE_DESIGN.md` 中的 `MULTIMODAL_DATA` 表

---

# **1. 多模态数据整体结构概览**

系统支持的多模态医疗数据类型包括：

| 模态类型 | 示例 | 后端识别方式 |
|---------|-------|--------------|
| 医学影像（CT/MRI/超声等） | JPG、BMP、PNG | `modality = 'image'` |
| 视频（手术流程、标准操作） | MP4 | `modality = 'video'` |
| 音频（护理录音等） | MP3 | `modality = 'audio'` |
| 文档（诊断结果、入院记录） | PDF | `modality = 'document'` |
| 基因序列数据 | FASTA、JPEG | `modality = 'genomic'` |
| 医疗设备数据 | PDF | `modality = 'device'` |

所有文件都存放在项目根目录的：

```
uploaded_files/
```


---

# **2. uploaded_files 目录结构说明**

完整结构如下：

```
uploaded_files/
│
├─medicaldata/
│  ├─MedicalImage/
│  │      CTImage1.jpg
│  │      MRIImage1.bmp
│  │      UltrasoundImage1.png
│  │
│  ├─AudioRecord/
│  │      心理咨询录音.mp3
│  │      术后护理录音.mp3
│  │
│  ├─StandardVideo/
│  │      手术流程视频.mp4
│  │
│  ├─Document/
│  │      AdmissionRecord1.pdf
│  │      DiagnosisResult1.pdf
│  │
│  ├─GenomicData/
│  │      GeneSequence1.fasta
│  │      AnalysisResult1.jpeg
│  │
│  ├─DeviceData/
│  │      DataContent1.pdf
│  │
│  └─MedicalRecord/
│         Prescription1.pdf
│
├─patient_blood_pressure/
│      patient_blood_pressure1.csv
│      …
│
├─patient_blood_sugar/
│      patient_blood_sugar1.csv
│      …
│
└─patient_temperature/
        patient_temperature1.csv
        …
```

下面将分模块进行说明：

---

# **3. medicaldata（多模态医疗数据）详细说明**

medicaldata 是整个系统的重点目录，用于存放 **多模态医疗业务文件**，并由 `MULTIMODAL_DATA` 表进行统一建模。

---

## **3.1 MedicalImage/（医学影像）**

存放：

- CT
- MRI
- 超声（B 超）

文件格式可能包括：

- `.jpg`
- `.jpeg`
- `.bmp`
- `.png`

后端中会将其识别为：

```
modality = "image"
file_format = "jpg" / "bmp" / "png"
```

---

## **3.2 AudioRecord/（音频记录）**

存放：

- 病情通知录音
- 心理咨询录音
- 护理录音

文件格式：

- `.mp3`

后端识别：

```
modality = "audio"
```

---

## **3.3 StandardVideo/（标准操作流程视频）**

存放：

- 手术流程
- 护理操作标准视频
- 应急处理流程视频

文件格式：

- `.mp4`

后端识别：

```
modality = "video"
```

---

## **3.4 Document/（医疗 PDF 文档）**

包括：

- 入院记录
- 出院小结
- 病历报告
- 治疗方案等

文件格式：

- `.pdf`

后端识别：

```
modality = "document"
```

---

## **3.5 GenomicData/（基因数据）**

包括：

- 基因序列 `.fasta`
- 分析结果图 `.jpeg`

识别方式：

```
modality = "genomic"
```

---

## **3.6 DeviceData/（设备数据）**

文件格式：

- `.pdf`

用途：

- 医疗设备输出的数据，如心电监护仪、检测仪等说明数据

识别方式：

```
modality = "device"
```

---

# **4. 时序生理数据目录（CSV 文件）**

系统还提供 3 类生理时间序列数据，每位患者一个 CSV 文件：

---

## **4.1 patient_blood_pressure/**

血压记录（收缩压/舒张压）

文件示例：

```
patient_blood_pressure5.csv
```

内容可能类似：

```
timestamp,systolic,diastolic
2024-01-01 08:00,120,80
2024-01-01 12:00,118,79
```

---

## **4.2 patient_blood_sugar/**

血糖记录：

```
patient_blood_sugar7.csv
```

---

## **4.3 patient_temperature/**

体温记录：

```
patient_temperature2.csv
```

---




# **5. 数据库结构 MULTIMODAL_DATA**

来自 `DATABASE_DESIGN.md`，该表用于记录文件元数据。

典型字段：

| 字段 | 类型 | 描述 |
|------|------|-------|
| `id` | VARCHAR | 主键，多模态记录 ID |
| `modality` | VARCHAR | 模态类型（image/audio/video/document/genomic/device） |
| `file_path` | VARCHAR | 文件在 uploaded_files 下的路径 |
| `file_format` | VARCHAR | 扩展名，如 `jpg`、`pdf` |
| `patient_id` | VARCHAR | 关联患者 |
| `record_id` | VARCHAR | 关联病历，可为空 |
| `source_table` | VARCHAR | 来源业务（可选） |
| `source_pk` | VARCHAR | 来源业务记录 ID |
| `description` | TEXT | 文件内容说明 |
| `text_content` | LONGTEXT | 文本内容，如 OCR、摘要、结构化记录 |
| `created_at` | DATETIME | 创建时间 |

---

# **6. 多模态 API 行为（app/api/multimodal.py）**

该模块包含：

| 接口 | 功能 |
|------|------|
| `GET /api/multimodal` | 列出记录 |
| `POST /api/multimodal` | 创建记录 |
| `GET /api/multimodal/file/<id>` | 下载/展示文件 |
| `DELETE /api/multimodal/<id>` | 删除记录 |

说明：

- `POST` 并不会上传真实文件，只记录 metadata  
  真实文件需先放入 `uploaded_files/...` 目录，再调用此接口登记

- `file/<id>` 会根据 `file_path` 读取硬盘文件流


---

# **7. insert_multimodal.py 的作用**

位于：

```
insert_data_python/insert_multimodal.py
```

作用：

- 扫描 `uploaded_files/medicaldata` 目录
- 识别文件模态和格式
- 自动向 `MULTIMODAL_DATA` 插入相应记录
- 按随机方式关联患者 ID、病历记录


流程：

```
扫描目录 → 判断模态 → 生成记录 ID → 插入 DB
```

---





# **8. 文档总结**

本文件解释了系统中：

- uploaded_files 目录每个子目录的含义  
- 多模态数据与数据库 MULTIMODAL_DATA 的关系  
- 多模态 API 如何读写文件  
- insert_multimodal.py 如何批量生成数据  
- 文件生命周期的设计思想   
---

