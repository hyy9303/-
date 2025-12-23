# MedData Hub

> **基于 React 19 + Python Flask 构建的全栈智能医院管理系统。**

<p align="center">
  <img src="https://img.shields.io/badge/React-19.0-blue?logo=react" />
  <img src="https://img.shields.io/badge/TypeScript-5.0-blue?logo=typescript" />
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-2.x-000000?logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

**MedData Hub** 是一个模拟现代化数字医院全流程的综合管理平台。项目采用前后端分离架构，集成了挂号分诊、电子病历、药房库存管理以及基于大模型的 AI 辅助诊断功能。

本项目采用 **"Hybrid Data Layer"（混合数据层）** 设计：前端支持连接真实的 Python 后端 API，亦可在无后端环境下通过本地 Mock 引擎全功能运行，实现演示环境 100% 可用。

---

## 核心特性 (Key Features)

### 前端交互 (Frontend)
* **混合架构**: “API 优先，Mock 兜底”策略，确保演示稳定性。
* **严格权限控制 (RBAC)**: 患者/医生/管理员三级权限体系，视图与操作完全隔离。
* **AI 智能集成**:
  * **影像诊断**: 集成多模态模型，支持 X 光/CT 片 AI 分析。
  * **RAG 问答**: 基于医院数据的上下文增强对话助手。
* **数据可视化**: 动态桑基图 (Sankey Diagram) 展示患者流转，运营数据大屏。

### 后端架构 (Backend)
* **模块化单体 (Modular Monolith)**: 基于 Flask Blueprint 实现业务领域隔离。
* **复杂业务逻辑**:
  * **事务脚本模式**: 确保病历写入与库存扣减的原子性。
  * **高级 SQL 查询** & 多表联查统计。
* **RESTful API**: 清晰接口定义，业务逻辑与数据访问完全分离。

---

## 项目文档 (Documentation)

本项目包含详尽的前后端架构、流程以及业务逻辑文档。

### 系统架构
* **[前端架构设计](./docs/FRONTEND_ARCHITECTURE.md)**  
* **[后端架构设计](./backend/BACKEND_ARCHITECTURE.md)**  
* **[API 接口文档](./backend/API_DOCUMENTATION.md)**  

---

## 🧩 Backend Documentation（后端文档）

后端文档按业务领域（Domain）和基础设施（Infrastructure）组织，涵盖 Flask 应用结构、业务 API、工具层、文件系统、多模态数据与初始化脚本。

### 🏛 架构与启动流程
| 文档 | 说明 |
|------|------|
| **[BACKEND_ARCHITECTURE.md](./backend/BACKEND_ARCHITECTURE.md)** | 后端整体架构设计与模块划分。 |
| **[BACKEND_APP_BOOTSTRAP.md](./backend/BACKEND_APP_BOOTSTRAP.md)** | Flask 启动流程、蓝图注册、日志系统、CORS。 |

### 🔐 认证模块
| 文档 | 说明 |
|------|------|
| **[BACKEND_API_AUTH.md](./backend/BACKEND_API_AUTH.md)** | 登录认证、角色体系与凭证校验逻辑。 |

### 🧑‍⚕️ 医疗业务核心模块
| 文档 | 描述 |
|------|------|
| **[BACKEND_API_PATIENT.md](./backend/BACKEND_API_PATIENT.md)** | 患者管理、患者统计、级联删除。 |
| **[BACKEND_API_DOCTOR.md](./backend/BACKEND_API_DOCTOR.md)** | 医生管理、科室关联、就诊队列。 |
| **[BACKEND_API_APPOINTMENT.md](./backend/BACKEND_API_APPOINTMENT.md)** | 挂号流程、自动分诊算法、挂号状态管理。 |
| **[BACKEND_API_BASIC.md](./backend/BACKEND_API_BASIC.md)** | 科室管理、药品管理（基础数据模块）。 |

### 📄 病历与处方
| 文档 | 描述 |
|------|------|
| **[BACKEND_API_RECORD.md](./backend/BACKEND_API_RECORD.md)** | 病历提交事务、处方管理、库存扣减流程。 |

### 🧬 多模态 & 统计
| 文档 | 描述 |
|------|------|
| **[BACKEND_API_MULTIMODAL.md](./backend/BACKEND_API_MULTIMODAL.md)** | 医学图像/音频/视频/文档等多模态资源管理。 |
| **[BACKEND_API_STATS.md](./backend/BACKEND_API_STATS.md)** | 数据统计接口、月度增长、桑基图等。 |

### 🛠 工具层
| 文档 | 描述 |
|------|------|
| **[BACKEND_UTILS.md](./backend/BACKEND_UTILS.md)** | 数据库连接池、时间戳校验、通用工具函数。 |

### 🗂 数据初始化
| 文档 | 描述 |
|------|------|
| **[BACKEND_DATA_INIT.md](./backend/BACKEND_DATA_INIT.md)** | 生成种子数据脚本、多模态数据初始化流程。 |

### 🗃️ 文件系统与多模态数据映射
| 文档 | 描述 |
|------|------|
| **[BACKEND_DATA_FILES_AND_MULTIMODAL.md](./backend/BACKEND_DATA_FILES_AND_MULTIMODAL.md)** | uploaded_files/ 结构说明、多模态文件与数据库映射关系。 |

---

## 快速开始 (Getting Started)

### 1. 环境准备
* Node.js (v18+) & Yarn  
* Python (3.8+)  
* MySQL (8.0+)

### 2. 克隆项目
```bash
git clone https://github.com/heavey0027/meddata-hub.git
cd meddata-hub
```

### 3. 后端启动 (Backend)
```bash
cd backend
pip install -r requirements.txt
python run.py
```

### 4. 前端启动 (Frontend)
```bash
cd ..
yarn
yarn dev
```

---

## 测试账号 (Demo Credentials)

| 角色 | 用户名 / ID | 密码 | 权限描述 |
|------|-------------|------|----------|
| 管理员 | admin | admin123 | 全局管理、数据大屏 |
| 医生 | DOC01 | password | 接诊台、处方、病历 |
| 患者 | P001 | password | 自助挂号、查看病历 |

---

## 技术栈 (Tech Stack)

### Frontend
React 19 · TypeScript · Vite · TailwindCSS · Lucide · Google Generative AI SDK

### Backend
Flask · MySQL · mysql-connector-python  
App Factory · Blueprint · Transaction Script Pattern

---

## License

本项目采用 MIT License 开源协议  
详见 [LICENSE](./LICENSE)


---
