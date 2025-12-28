# **BACKEND_APP_BOOTSTRAP.md**
本文件详细说明系统后端 Flask 应用的启动方式、架构入口、全局中间件、日志初始化、蓝图注册、请求生命周期钩子等内容。

---

# **1. 模块概览**

系统后端采用 **Flask + 蓝图（Blueprint）** 的模块化结构。应用启动的关键文件为：

| 文件路径 | 作用 |
|---------|------|
| `run.py` | 项目启动入口 |
| `backend/app/__init__.py` | 应用工厂函数、日志初始化、蓝图注册、全局钩子等全部入口逻辑 |

整个后端的所有 API 都通过 `create_app()` 注册并生效。

---

# **2. 启动文件：run.py**

位于：

```
backend/run.py
```

核心内容如下（已基于最新文件内容确认）：

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
```

### **作用说明**

| 功能 | 说明 |
|------|------|
| 创建应用实例 | 调用 `create_app()` |
| 启动开发服务器 | Flask 内置服务器（仅 dev 用） |
| 监听端口 | 默认 `0.0.0.0:5000` |


---

# **3. 应用工厂：backend/app/__init__.py**

这是整个系统最核心的初始化文件，负责：

- 创建 Flask 实例  
- 启用 CORS  
- 初始化日志  
- 注册所有 API 蓝图（auth / appointment / record / multimodal 等）  
- 注册全局请求前置校验（时间戳）  
- 测试根路由  

## **3.1 create_app() — 系统初始化流程**

源码结构如下：

```python
def create_app():
    app = Flask(__name__)
    CORS(app)

    # 初始化日志
    setup_logging()

    # 注册 API 蓝图
    from app.api.auth import auth_bp
    from app.api.basic import basic_bp
    from app.api.doctor import doctor_bp
    from app.api.patient import patient_bp
    from app.api.record import record_bp
    from app.api.appointment import appointment_bp
    from app.api.stats import stats_bp
    from app.api.multimodal import multimodal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(basic_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(record_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(multimodal_bp)

    # 全局请求前置校验
    @app.before_request
    def before_request():
        error = check_timestamp()
        if error:
            return error

    @app.route('/')
    def index():
        return "MedData Hub API is running..."

    return app
```

### **初始化流程图**

```
create_app()
 ├── 创建 Flask 实例
 ├── 启用 CORS
 ├── 初始化日志 setup_logging()
 ├── 注册 8 个 API 蓝图
 ├── 注册 before_request 全局钩子（时间戳校验）
 ├── 注册根路由 /
 └── 返回 app 实例
```

---

# **4. API 蓝图注册**

系统采用 **分模块路由结构**，所有蓝图均在 `app/api/` 下实现。

## **4.1 已注册的蓝图（按加载顺序）**

| 蓝图 | 路径 | 主要功能 |
|------|------|-----------|
| `auth_bp` | `app/api/auth.py` | 登录 |
| `basic_bp` | `app/api/basic.py` | 科室、药品等基础数据 |
| `doctor_bp` | `app/api/doctor.py` | 医生相关 API |
| `patient_bp` | `app/api/patient.py` | 患者 CRUD 与统计 |
| `record_bp` | `app/api/record.py` | 病历 + 处方 |
| `appointment_bp` | `app/api/appointment.py` | 挂号系统 |
| `stats_bp` | `app/api/stats.py` | 各类统计，包括桑基图等 |
| `multimodal_bp` | `app/api/multimodal.py` | 多模态文件管理（图像/视频/音频/基因数据等） |

### 所有 API 都带 `/api` 前缀  
例如：

- `/api/login`
- `/api/appointments`
- `/api/multimodal/file/<id>`

---

# **5. 日志系统 setup_logging()**

文件位置：

```
backend/app/__init__.py
```

功能：

- 设置全局日志等级为 INFO
- 防止重复添加 handler（Flask reload 时避免重复输出）
- 创建 StreamHandler 输出日志到控制台

代码结构如下（保持原样）：

```python
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
```

特点：

| 优点 | 缺点 |
|------|------|
| 简洁、安全（避免重复 handler） | 无文件日志、无区分 API 访问日志、无结构化日志 |


---

# **6. 全局请求前置钩子 before_request()**

依赖模块：

```
app/utils/common.py: check_timestamp()
```

功能：

- 校验请求中的 `_t` 时间戳（毫秒）
- 若与服务器时间差超过 5 分钟 → **reject**

目的：

- 简单防止重放攻击
- 统一校验所有 API（无需每个接口单独处理）

---

# **7. 根路由 `/`**

返回：

```
"MedData Hub API is running..."
```

用于：

- 健康检查  
- 服务启动验证  

---

# **8. 模块之间的依赖结构**

```
run.py → create_app()
create_app() ├─ setup_logging()
             ├─ register_blueprints(...)
             ├─ before_request(check_timestamp)
             └─ index()
```

API 蓝图依赖：

- `utils/db.py` 获取数据库连接  
- `utils/common.py` 时间戳工具  
- 多模态模块依赖 uploaded_files 物理存储  
- record / appointment 等核心模块依赖数据库事务  

---

# **9. 总体架构总结**

`BACKEND_APP_BOOTSTRAP` 模块扮演整个系统的“大脑”，协调各模块启动：

| 组件 | 说明 |
|------|------|
| Flask 应用实例 | 所有服务的容器 |
| 蓝图系统 | 按功能模块划分路由 |
| 日志初始化 | 全局日志配置 |
| CORS | 允许跨域 |
| before_request | 全局请求拦截逻辑 |
| index | 健康检查 |

系统结构清晰、可扩展性高。

---
