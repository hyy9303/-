# **BACKEND_UTILS.md**

本文件用于对后端系统中的 **工具层（Utilities Layer）** 进行全面说明，包括数据库连接管理、全局工具函数、时间戳校验规则以及这些工具在后端中的使用方式。

后端工具模块位于：

```
app/utils/
    ├── db.py
    ├── common.py
    └── __init__.py
```

工具层是所有 API 模块的基础设施组件，被所有业务模块调用。

---

# **1. 模块总览**

| 模块文件 | 功能 |
|----------|------|
| `db.py` | 数据库连接池管理、统一获取连接 |
| `common.py` | 通用工具函数（时间戳校验、基础格式化工具） |

后端中所有和数据库交互的 API 都依赖 `db.get_db_connection()` 创建连接，所有请求都会经过 `common.check_timestamp()` 的时间戳校验。

---

# **2. 数据库工具：db.py**

## **2.1 概述**

该模块负责：

- 初始化 MySQL 连接池（MySQL Connector / Pooling）
- 提供统一的数据库连接函数 `get_db_connection()`
- 管理连接的生命周期（由业务模块 commit / rollback / close）

项目路径：

```
app/utils/db.py
```

---

# **2.2 连接池配置**

代码核心部分如下：

```python
import mysql.connector
from mysql.connector import pooling

db_config = {
    "pool_name": "medpool",
    "pool_size": 32,
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "meddata_hub",
    "autocommit": False
}

pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
```

### **参数说明**

| 参数 | 含义 |
|------|------|
| `pool_name` | 连接池名称 |
| `pool_size` | 最大连接数 |
| `autocommit=False` | 所有写操作必须显式 commit 才会生效（保证事务一致性） |
| `user/password` | 数据库账户 |
| `database` | 默认数据库名：`meddata_hub` |

---

# **2.3 获取数据库连接**

API 模块调用数据库必须使用：

```python
from app.utils.db import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
```

函数定义：

```python
def get_db_connection():
    try:
        connection = pool.get_connection()
        return connection
    except mysql.connector.Error as err:
        print(f"Error getting connection: {err}")
        raise err
```

### **返回值**

- 一个从连接池中获取的 MySQL 连接对象
- 不会自动提交事务（需要业务模块处理）

---

# **2.4 使用规范**

所有 API 模块必须遵守以下模板：

```python
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

try:
    # 执行 SQL
    cursor.execute(...)
    conn.commit()
except Exception as e:
    conn.rollback()
    raise e
finally:
    cursor.close()
    conn.close()  # 必须关闭，否则连接不会回到连接池
```


---

# **2.5 错误处理约定**

`get_db_connection()` 本身不会吞掉 MySQL 异常，而是抛给上层，让 API 层做统一错误响应：

- 业务模块在 `try/except` 内捕获并打印日志
- 返回 `500 Internal Server Error` 给前端

---

# **3. 通用工具：common.py**

## **3.1 概述**

`common.py` 提供以下功能：

- 请求时间戳校验（全局防重放）
- 日期格式转换辅助函数（目前为预留能力）

路径：

```
app/utils/common.py
```

---

# **3.2 时间戳校验 check_timestamp**

系统在 `app/__init__.py` 中注册：

```python
@app.before_request
def before_request():
    error = check_timestamp()
    if error:
        return error
```

意味着：

**所有 API 请求都必须带 `_t` 参数，否则校验失败。**

### **函数定义**

```python
def check_timestamp():
    request_time = request.args.get('_t')
    if not request_time:
        return None

    try:
        request_time = int(request_time)
    except ValueError:
        return "Invalid timestamp format", 400

    current_time = int(time.time() * 1000)

    if abs(current_time - request_time) > 5 * 60 * 1000:
        return "Timestamp is too old or too far in the future", 400

    return None
```

---

# **3.3 时间戳规则说明**

| 项目 | 内容 |
|------|------|
| 参数名 | `_t` |
| 单位 | 毫秒（ms） |
| 可接受偏差 | ±5 分钟 |
| 校验失败返回 | `400` 错误 |

### **设计目的**

- 防止重放攻击（基本级别的安全措施）
- 防止客户端时间错误造成的数据不一致
- 所有 API 自动拥有该安全校验（无需业务代码参与）

### **示例**

正确请求：

```
GET /api/patients?_t=1705800000000
```

错误示例（时间过期）：

```
400 Timestamp is too old or too far in the future
```

---

# **3.4 format_date 函数**

目前版本只做简单转换：

```python
def format_date(d):
    return str(d) if d else None
```


---

# **4. utils 模块在整个后端系统中的角色**

### **4.1 模块作用关系**

```
app/api/*  →  utils/db.py  →  MySQL数据库
app/api/*  →  utils/common.py (check_timestamp)
app/__init__.py → before_request → check_timestamp()
```

### **每个 API 模块都依赖 utils 层**

示例（appointment.py、patient.py、record.py 等）：

- 使用数据库连接池提供连接
- 使用 timestamp 校验保护请求

因此 utils 是整个后端的基础设施层（Infrastructure Layer）。


# **5. 文档总结**

本文件描述了 utils 层在后端中的所有核心功能：

| 模块 | 说明 |
|------|------|
| db.py | 构建并管理 MySQL 连接池，所有数据库操作的基础 |
| common.py | 通用工具函数；所有 API 的全局请求校验（时间戳） |



---
