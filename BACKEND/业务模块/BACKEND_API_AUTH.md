# BACKEND_API_AUTH.md
---
## 1. 模块概览

- **模块文件**：`app/api/auth.py`  
- **蓝图名称**：`auth_bp`  
- **主要职责**：  
  - 提供统一的**用户登录认证接口**；  
  - 根据不同用户角色（`patient` / `doctor` / `admin`）到对应表中校验账号密码；  
  - 返回登录成功与否及用户基础信息。

系统中使用的用户实体与数据库表对应关系（见 `DATABASE_DESIGN.md`）：

- 患者 → 表：`PATIENTS`
- 医生 → 表：`DOCTORS`
- 管理员 → 当前实现中与医生/专门管理员表关联

---

## 2. 路由与接口概览

### 2.1 登录接口：`POST /api/login`

- **蓝图**：`auth_bp`
- **路由定义位置**：`app/api/auth.py`

```python
@auth_bp.route('/api/login', methods=['POST'])
def login():
    ...
```

- **功能说明**：  
  接收用户提交的账号、密码和角色信息，到对应的数据库表中进行校验；若认证通过，返回用户基础信息；否则返回错误消息。

---

## 3. 请求与响应设计

### 3.1 请求格式

- **HTTP 方法**：`POST`
- **URL**：`/api/login`
- **Header**：`Content-Type: application/json`
- **请求体 JSON**

```json
{
  "id": "用户编号（患者编号 / 医生编号 / 管理员编号）",
  "password": "登录密码（当前为明文校验）",
  "role": "patient | doctor | admin"
}
```

字段说明：

| 字段名    | 类型   | 是否必填 | 说明                                      |
|-----------|--------|----------|-------------------------------------------|
| `id`      | string | 是       | 用户编号：`PATIENTS.id` 或 `DOCTORS.id` |
| `password`| string | 是       | 登录密码，对应表中的 `password` 字段     |
| `role`    | string | 是       | 角色：`patient` / `doctor` / `admin`      |

---

### 3.2 响应格式

#### 3.2.1 登录成功

```json
{
  "success": true,
  "data": {
    "id": "P001",
    "name": "张三",
    "role": "patient",
    "...": "其他与角色相关的基础信息"
  }
}
```

- `data` 中的字段来自对应用户表（`PATIENTS` / `DOCTORS` 等），典型包括：
  - 患者：`id`, `name`, `gender`, `age`, `phone`, `address`, `create_time` 等；
  - 医生：`id`, `name`, `title`, `specialty`, `phone`, `department_id` 等；

#### 3.2.2 登录失败：账号或密码错误

```json
{
  "success": false,
  "message": "账号或密码错误"
}
```

- HTTP 状态码：`401`
- 触发条件：
  - 根据 `id + role` 在数据库中未找到对应用户；
  - 找到用户但 `password` 不匹配；

模块中会记录 warning 级别日志，例如：

```python
logger.warning("Password mismatch for user: %s", user_id)
```

#### 3.2.3 服务器内部错误

```json
{
  "success": false,
  "message": "服务器内部错误"
}
```

- HTTP 状态码：`500`
- 触发条件：
  - 与数据库连接失败；
  - SQL 执行异常；
  - 其他未捕获的运行时异常。

模块中会记录 error 级别日志：

```python
logger.error("Login error: %s", e)
```

---

## 4. 认证流程设计

以下是 `login()` 函数的业务逻辑流程：

1. **解析请求体**

   ```python
   data = request.json
   user_id = data.get('id')
   password = data.get('password')
   role = data.get('role')  # 'patient', 'doctor', 'admin'
   ```


2. **获取数据库连接**

   ```python
   conn = get_db_connection()
   cursor = conn.cursor(dictionary=True)
   ```

   - 调用 `app.utils.db.get_db_connection()` 从连接池获取连接；
   - `dictionary=True` 使查询结果以字典形式返回，便于直接转成 JSON。

3. **根据角色选择数据表**

   - 当 `role == 'patient'` → 查询 `PATIENTS` 表：
     - 字段定义见 `DATABASE_DESIGN.md` 中：

       ```text
       PATIENTS {
           string id PK "患者编号"
           string name "姓名"
           string password "密码"
           string gender "性别"
           int age "年龄"
           string phone "电话"
           string address "地址"
           date create_time "建档日期"
       }
       ```

   - 当 `role == 'doctor'` → 查询 `DOCTORS` 表：

       ```text
       DOCTORS {
           string id PK "医生编号"
           string name "姓名"
           string password "密码"
           string title "职称"
           string specialty "专业领域"
           string phone "电话"
           string department_id FK "所属科室"
       }
       ```



4. **执行查询并校验密码**

   - 根据 `id` 从相应表中查询用户记录；
   - 若未查询到记录：
     - 返回 `401` + `{"success": false, "message": "账号或密码错误"}`；
   - 若查询到记录，则比较请求中的 `password` 与记录中的 `password` 字段：
     - 完全相同 → 登录成功，返回用户基础信息；
     - 不相同 → 记录 `logger.warning`，返回 401。

5. **构造返回 JSON**

   - 登录成功时，从查询结果中删除 `password` 字段（安全起见），仅返回必要的非敏感信息；
   - 返回结构类似：

     ```python
     return jsonify({
         "success": True,
         "data": {
             "id": row["id"],
             "name": row["name"],
             "role": role,
             # ... 其他字段
         }
     })
     ```

6. **异常处理**

   - 在 `try/except` 块中捕获所有异常 `Exception as e`；
   - 打印错误日志并返回 `500` 状态码和通用错误消息。

7. **资源释放**

   - 在 `finally` 中关闭 `cursor` 与 `conn`：

     ```python
     finally:
         if cursor: cursor.close()
         if conn: conn.close()
     ```

   - 确保所有数据库资源被正确归还到连接池中。

---


## 5. 与其他模块的关系

- **上游调用方**
  - 前端登录页面/应用；
  - 第三方系统（如后续集成的 HIS、LIS 等）也可以通过该接口做简单认证。

- **下游依赖**
  - `app.utils.db.get_db_connection()`：数据库连接池；
  - 数据库表：`PATIENTS`、`DOCTORS`；
  - 日志系统：`logging.getLogger(__name__)` 统一日志输出。

- **配合模块**
  - 后续业务接口（挂号、病历、多模态数据等）可要求前端携带登录接口返回的用户 ID 与 role，进行权限控制与数据范围过滤。

---

## 6. 小结

`auth.py` 模块为完整后端提供了统一的登录入口：

- 采用 **单一接口 `/api/login` + 多角色** 的设计；
- 通过数据库表 `PATIENTS` / `DOCTORS` 等完成账号密码校验；
- 在异常情况下保证数据库资源回收与日志记录。
