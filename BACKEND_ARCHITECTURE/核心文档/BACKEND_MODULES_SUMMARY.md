# `BACKEND_MODULES_SUMMARY.md`

# 后端模块文档总览（Backend Documentation Summary）

本文件用于总结当前后端项目（Backend）下所有 `.md` 文档的作用，帮助开发者快速理解每份文档的目的及对应的代码模块。

---

## 1. 应用启动与基础设施

### **BACKEND_APP_BOOTSTRAP.md**
- **作用**：描述后端 Flask 应用如何启动、如何加载配置、如何注册蓝图。
- **对应代码目录**：
  - `run.py`
  - `app/__init__.py`
- **主要内容**：
  - `create_app()` 的执行流程
  - CORS、日志系统、请求前置钩子（时间戳校验）
  - 蓝图注册机制

---

## 2. API 模块文档（按功能划分）

每个文档对应 `app/api/` 下的一个 Python 模块。

---

### **BACKEND_API_AUTH.md**
- **作用**：说明用户认证（登录）模块的 API。
- **对应代码**：`app/api/auth.py`
- **内容**：
  - 登录请求与验证逻辑
  - 错误处理方式
  - 登录成功返回的用户信息说明

---

### **BACKEND_API_BASIC.md**
- **作用**：说明基础数据模块 API，如科室、药品。
- **对应代码**：`app/api/basic.py`
- **内容**：
  - 科室查询 / 新增 / 删除
  - 药品查询 / 更新 / 删除

---

### **BACKEND_API_DOCTOR.md**
- **作用**：描述医生相关业务的 API。
- **对应代码**：`app/api/doctor.py`
- **内容**：
  - 医生列表、医生详情
  - 医生与科室的关系
  - 医生删除限制条件（有病历/挂号时不可删除）

---

### **BACKEND_API_PATIENT.md**
- **作用**：说明患者管理相关 API。
- **对应代码**：`app/api/patient.py`
- **内容**：
  - 添加、更新、删除患者
  - 患者统计（年龄结构、性别比例等）
  - 级联删除（如删除患者时同时删除挂号/病历）

---

### **BACKEND_API_APPOINTMENT.md**
- **作用**：说明挂号业务流程与 API。
- **对应代码**：`app/api/appointment.py`
- **内容**：
  - 患者挂号流程
  - 自动分配医生算法（按医生当前挂号量）
  - 挂号状态更新与统计接口

---

### **BACKEND_API_RECORD.md**
- **作用**：病历、处方相关业务的 API 文档。
- **对应代码**：`app/api/record.py`
- **内容**：
  - 新建病历
  - 提交处方（包含事务处理与库存扣减逻辑）
  - 查询病历与处方明细
  - 删除病历（含级联处理）

---

### **BACKEND_API_MULTIMODAL.md**
- **作用**：描述多模态数据（图像 / 视频 / 音频 / 文档等）接口。
- **对应代码**：`app/api/multimodal.py`
- **内容**：
  - 多模态数据的上传、删除、查询
  - 文件路径与数据库记录之间的映射
  - 模态分类（image / audio / genomic / video 等）

---

### **BACKEND_API_STATS.md**
- **作用**：提供统计分析类 API。
- **对应代码**：`app/api/stats.py`
- **内容**：
  - 桑基图数据生成接口
  - 月度变化 / 环比统计接口

---

## 3. 工具与基础设施层

### **BACKEND_UTILS.md**
- **作用**：说明后端公共工具模块。
- **对应目录**：`app/utils/`
- **内容**：
  - `db.py`：数据库连接池、连接获取规范
  - `common.py`：通用函数（如时间戳校验）
  - 业务模块如何依赖这些工具

---

## 4. 数据初始化与示例数据

### **BACKEND_DATA_INIT.md**
- **作用**：说明项目中的数据初始化脚本及其用途。
- **对应目录**：`insert_data_python/`
- **内容**：
  - 大规模数据生成脚本（`insert_data.py`）
  - Demo 小数据脚本（`insert_small_data.py`）
  - 多模态数据初始化（`insert_multimodal.py`）
  - 桑基图数据初始化（`insert_sankey.py`）
  - 初始数据的加载顺序和使用场景

---

## 5. 多模态文件存储设计

### **BACKEND_DATA_FILES_AND_MULTIMODAL.md**
- **作用**：说明项目中用于存放文件的目录结构与设计原则。
- **对应目录**：`uploaded_files/`
- **内容**：
  - 图像、音频、视频、基因数据、文档等文件分类
  - 文件路径与 `MULTIMODAL_DATA` 数据库表的关联规则
  - 如何新增文件、如何被后端识别

---
