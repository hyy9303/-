
# MedData Hub 后端架构文档 (重构版)

## 1. 项目概述
本项目是一个基于 **Python Flask** 框架开发的医疗数据管理系统（MedData Hub）后端服务。

经过架构重构，项目已从初始的单文件脚本演进为**模块化单体架构 (Modular Monolith)**。系统利用 Flask 的 **Blueprints（蓝图）** 和 **Application Factory（应用工厂）** 模式，实现了业务逻辑的物理隔离与解耦。它提供了一套 RESTful API，用于处理医院的挂号、病历管理、患者管理、医生排班以及药品库存管理等核心业务。

## 2. 技术栈 (Tech Stack)

| 组件 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **编程语言** | Python 3.x | 后端核心逻辑 |
| **Web 框架** | Flask | 核心 Web 容器 |
| **模块化方案** | Flask Blueprints | 实现业务领域的路由隔离 |
| **数据库** | MySQL | 关系型数据库存储 |
| **数据库驱动** | mysql-connector-python | 官方驱动，使用 **Connection Pooling** |
| **跨域处理** | Flask-CORS | 解决前后端分离开发时的跨域问题 |
| **日志系统** | Python Logging | 全局单例日志配置 (`app.log`) |

## 3. 系统架构设计

### 3.1 架构分层
系统遵循典型的三层架构模式，各层职责清晰：

1.  **表现层 (Presentation Layer)**:
    *   由 `app/api/` 下的各个蓝图文件定义。
    *   负责路由分发、HTTP 请求解析、参数验证及响应格式化。
2.  **业务逻辑层 (Business Logic Layer)**:
    *   嵌入在各个路由处理函数中（采用**事务脚本模式**）。
    *   负责执行具体的业务规则（如：库存检查、重复挂号校验、自动分配医生）。
3.  **基础设施层 (Infrastructure Layer)**:
    *   `app/utils/db.py`: 提供数据库连接池管理。
    *   `app/utils/common.py`: 提供通用辅助工具。

### 3.2 目录结构 (Directory Structure)
```text
MedDataHub/backend
├── run.py                   # [门面模式] 应用程序唯一入口
├── app/                     # [核心包] 应用主体
│   ├── __init__.py          # [工厂模式] 应用工厂与配置中心
│   ├── utils/               # [工具层]
│   │   ├── db.py            # 数据库连接池 (单例)
│   │   └── common.py        # 通用工具函数
│   └── api/                 # [接口层] 按业务领域拆分的蓝图
│       ├── auth.py          # 认证域 (登录)
│       ├── basic.py         # 基础数据域 (科室、药品)
│       ├── doctor.py        # 医生域
│       ├── patient.py       # 患者域
│       ├── stats.py         # 统计数据域
│       ├── multimodal.py    # 多模态域
│       ├── record.py        # 病历与处方域
│       └── appointment.py   # 挂号与统计域
└── app.log                  # 运行时日志
```

## 4. 核心设计模式 (Core Design Patterns)

本项目在重构过程中严格遵循了以下软件工程设计模式：

### 4.1 应用工厂模式 (Application Factory Pattern)
*   **实现位置**: `app/__init__.py` -> `create_app()`
*   **模式说明**: 不再使用全局的 `app` 对象，而是在函数中创建应用实例。
*   **价值**:
    *   **解耦**: 将应用的创建逻辑与全局作用域解耦，避免循环引用。
    *   **可扩展性**: 允许在运行时动态注册配置和蓝图。

### 4.2 模块化模式 / 蓝图 (Modular Pattern via Blueprints)
*   **实现位置**: `app/api/*.py`
*   **模式说明**: 将庞大的应用拆分为一组独立的模块（Auth, Patient, Doctor等）。
*   **价值**:
    *   **关注点分离 (SoC)**: 每个文件只关注自己的业务领域，便于多人协作。
    *   **路由命名空间**: 物理隔离不同业务的路由定义。

### 4.3 事务脚本模式 (Transaction Script Pattern)
*   **实现位置**: 各个 API 路由函数内部 (如 `create_record` 的内部逻辑)
*   **模式说明**: 业务逻辑被组织成单个过程（脚本），每个过程处理一个来自表现层的请求。
*   **价值**:
    *   鉴于项目直接使用原生 SQL 而非 ORM，事务脚本模式是最自然的选择。它将校验、计算、数据库事务控制（Start/Commit/Rollback）封装在一个函数流中。

### 4.4 单例模式 (Singleton Pattern)
*   **实现位置**: `app/utils/db.py` (连接池) 和 `logging` 配置
*   **模式说明**: 确保一个类只有一个实例，并提供一个全局访问点。
*   **价值**:
    *   确保整个应用生命周期内，数据库连接池和日志处理器只被初始化一次，节省资源并防止连接泄露。

### 4.5 外观模式 (Facade Pattern) [额外补充]
*   **实现位置**: RESTful API 接口层
*   **模式说明**: 为子系统中的一组接口提供一个一致的界面。
*   **价值**:
    *   后端 API 屏蔽了底层复杂的数据库表结构（如 `doctors` 表和 `appointments` 表的联合统计）。前端只需调用 `/api/doctors`，无需了解底层复杂的 SQL 关联逻辑。

## 5. 关键业务逻辑与 SQL 实现

尽管架构进行了拆分，但核心的高级数据库操作逻辑得以完整保留并在各自的模块中运行：

### 5.1 复杂查询 (Read Operations)
*   **相关子查询 (Correlated Subquery)** -> `api/doctor.py`:
    *   计算每位医生当前的待处理挂号数量。
*   **关系除法/全称量词 (Relational Division)** -> `api/patient.py`:
    *   识别“VIP患者”（去过所有科室的患者），使用双重 `NOT EXISTS` 实现。

### 5.2 事务处理 (Write Operations)
*   **病历提交事务** -> `api/record.py`:
    *   通过 `conn.start_transaction()` 保证病历主表与处方明细表的原子性写入，包含库存的强校验。
*   **挂号自动分配** -> `api/appointment.py`:
    *   结合 `GROUP BY` 和聚合函数，实现基于医生负载的自动排班逻辑。

## 6. 部署与运行

*   **入口文件**: `run.py`
*   **启动命令**: `python run.py`
*   **配置**: 数据库配置位于 `app/utils/db.py`。
*   **扩展性**: 新增业务模块只需在 `app/api/` 下新建文件，并在 `app/__init__.py` 中注册即可，无需修改核心逻辑。