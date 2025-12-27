# **BACKEND_DATA_INIT.md**  
> **MedData Hub 后端数据库初始化与数据生成说明文档**  

---

# **1. 文档目的**

本说明文档用于描述系统后端 **数据库初始化流程**、**数据生成脚本**、**多模态数据导入机制** 以及 **统计数据初始化方法**。  

后端所有业务逻辑（患者管理、医生管理、挂号、病历、处方、多模态文件、统计分析）均依赖这些初始化脚本提供的基础数据与数据库结构。

---

# **2. 文件结构**

项目中与数据初始化相关的文件位于：

```
insert_data_python/
│
├── meddata_hub.sql
├── insert_data.py
├── insert_small_data.py
├── insert_multimodal.py
├── insert_sankey.py
```

---

# **3. 数据库初始化：meddata_hub.sql**

数据库 schema 文件：

```
insert_data_python/meddata_hub.sql
```

包含系统所有表定义，包括但不限于：

| 表名 | 用途 |
|------|------|
| `DEPARTMENTS` | 医院科室 |
| `DOCTORS` | 医生信息 |
| `PATIENTS` | 患者信息 |
| `MEDICINES` | 药品基础数据 |
| `APPOINTMENTS` | 挂号记录 |
| `MEDICAL_RECORDS` | 病历主表 |
| `PRESCRIPTION_DETAILS` | 处方明细 |
| `MULTIMODAL_DATA` | 多模态文件索引数据 |
| `STAT_FLOW` | 桑基图或统计数据相关表 |

### **使用方式**

首次部署后端时必须执行：

```sql
mysql -u root -p < meddata_hub.sql
```



---

# **4. insert_data.py — 大规模模拟数据生成脚本**

文件路径：

```
insert_data_python/insert_data.py
```

### **功能概述**

该脚本用于 **构造完整业务场景的大规模模拟数据**，包括：

| 数据类型 | 是否生成 | 说明 |
|----------|----------|------|
| 科室（DEPARTMENTS） | ✔ | 系统初始化基础科室类别 |
| 医生（DOCTORS） | ✔ | 每个科室随机分配若干医生 |
| 患者（PATIENTS） | ✔ | 使用 Faker 批量生成姓名、年龄、电话等 |
| 挂号记录（APPOINTMENTS） | ✔ | 患者→科室→医生 |
| 病历（MEDICAL_RECORDS） | ✔ | 随机疾病描述、诊断内容 |
| 处方（PRESCRIPTION_DETAILS） | ✔ | 随机药品及数量 |
| 随机日期 | ✔ | 分布于模拟年份内，用于统计模块 |


### **执行方式**

```bash
python insert_data_python/insert_data.py
```


---

# **5. insert_small_data.py — 小规模快速模拟数据**

文件路径：

```
insert_data_python/insert_small_data.py
```

### **功能概述**

- 类似 `insert_data.py`，但**数据体量较小**，通常几十条到几百条。

### **执行方式**

```bash
python insert_data_python/insert_small_data.py
```


---

# **6. insert_multimodal.py — 多模态数据初始化脚本**

文件路径：

```
insert_data_python/insert_multimodal.py
```

### **功能**

该脚本会扫描以下目录结构：

```
uploaded_files/medicaldata/
│
├── MedicalImage/
├── AudioRecord/
├── StandardVideo/
├── Document/
├── DeviceData/
├── GenomicData/
└── ...
```

并将文件以多模态记录的形式写入数据库表：

```
MULTIMODAL_DATA
```

### **写入内容包括：**

| 字段 | 来源 |
|------|------|
| `file_path` | 文件相对路径，例如：`medicaldata/MedicalImage/CTImage1.jpg` |
| `modality` | 根据目录自动识别（image/audio/video/document/genomic 等） |
| `file_format` | 文件扩展名 |
| `patient_id` | 脚本可能按规则分配（如随机或按文件名推断） |
| `record_id` | 若存在病历关联，将绑定对应病历 |
| `description` | 根据文件名自动生成或留空 |
  

### **执行方式**

```bash
python insert_data_python/insert_multimodal.py
```


---

# **7. insert_sankey.py — 统计图表数据初始化**

文件路径：

```
insert_data_python/insert_sankey.py
```

### **功能**

- 为 `/api/stats/sankey` 提供示例性流向数据

### **关联模块**

- `app/api/stats.py`

### **执行方式**

```bash
python insert_data_python/insert_sankey.py
```

---

# **8. 初始化顺序**

系统初始化按以下顺序执行脚本：

### **（1）建表**

```
mysql < meddata_hub.sql
```

### **（2）插入基础业务数据**

可选其中之一：

| 脚本 | 用途 |
|------|------|
| `insert_small_data.py` | 快速构建小型数据集 |
| `insert_data.py` | 构建大型模拟数据集 |

### **（3）插入多模态数据**

```
python insert_multimodal.py
```


### **（4）插入统计图示数据**

```
python insert_sankey.py
```

---
