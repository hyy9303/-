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
- 管理员 → 当前实现中通常与医生/专门管理员表关联（视后续实现扩展）

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

> 当前实现中，`password` 存储在数据库中为明文字段（`PATIENTS.password`, `DOCTORS.password`）。后续可升级为哈希存储。

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
- 当前实现中没有生成 JWT 或 session，只返回用户基础信息，供前端后续携带使用。

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

以下是 `login()` 函数的业务逻辑流程（结合源码与数据库设计文档归纳）：

1. **解析请求体**

   ```python
   data = request.json
   user_id = data.get('id')
   password = data.get('password')
   role = data.get('role')  # 'patient', 'doctor', 'admin'
   ```

   - 若某些字段缺失，当前实现中可能会触发异常并走到统一异常处理（500）。  
   - 可以在后续增强输入校验（返回 400 + 详细字段错误提示）。

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

   - 当 `role == 'admin'`：
     - 当前源码中使用 `role` 字段，但具体管理员存储策略在 `auth.py` 中被 `...` 省略；
     - 常见实现策略包括：
       - 独立的 `ADMINS` 表；
       - 或在 `DOCTORS` 表中通过某个标志字段（如 `is_admin`）区分。

   > 由于源码中 SQL 细节用 `...` 省略，文档在此采用“逻辑层面”的描述，具体实现请以实际 SQL 为准。

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

## 5. 安全性与后续改进建议

当前认证模块实现简洁直接，更接近“教学 & Demo 用途”，在真实生产环境可进一步增强：

1. **密码安全**

   - **当前**：密码以明文形式存储在 `PATIENTS.password` / `DOCTORS.password` 并做明文比对；
   - **建议**：
     - 数据库存储密码哈希（如 `bcrypt` / `PBKDF2` / `argon2`）；
     - 登录时使用相同算法对输入密码做哈希比对；
     - 明确禁止在任何 API 响应中返回 `password` 字段。

2. **认证令牌（Token / Session）**

   - **当前**：登录成功仅返回基本用户信息，没有 token；
   - **建议**：
     - 引入 **JWT**（JSON Web Token）或其他 token 机制；
     - 登录成功时签发 token：
       - token 中包含 `sub`（用户ID）、`role`、过期时间 `exp` 等；
     - 其他业务 API 使用 `Authorization: Bearer <token>` 进行鉴权；
     - 配合 `before_request` 中的校验实现统一认证授权。

3. **输入校验**

   - 对 `id` / `password` / `role` 做严格的非空校验与类型校验；
   - 对 `role` 限制在允许的枚举范围内；
   - 若参数不合法，应返回 `400 Bad Request`，避免直接抛异常。

4. **防暴力破解与风控**

   - 对同一账号 / IP 一定时间内的登录失败次数做限制；
   - 达到阈值后可以：
     - 暂时锁定账号；
     - 或增加图形验证码 / 短信验证码等多因素验证。

5. **审计日志**

   - 对登录成功 / 失败事件打详细审计日志，包括：
     - 用户 ID、角色；
     - 来源 IP、User-Agent；
     - 登录结果；
   - 日志中严禁记录明文密码。

---

## 6. 与其他模块的关系

- **上游调用方**
  - 前端登录页面/应用；
  - 第三方系统（如后续集成的 HIS、LIS 等）也可以通过该接口做简单认证。

- **下游依赖**
  - `app.utils.db.get_db_connection()`：数据库连接池；
  - 数据库表：`PATIENTS`、`DOCTORS`（以及可能的管理员相关表）；
  - 日志系统：`logging.getLogger(__name__)` 统一日志输出。

- **配合模块**
  - 后续业务接口（挂号、病历、多模态数据等）可要求前端携带登录接口返回的用户 ID 与 role，进行权限控制与数据范围过滤。

---

## 7. 小结

`auth.py` 模块为完整后端提供了统一的登录入口：

- 采用 **单一接口 `/api/login` + 多角色** 的设计；
- 通过数据库表 `PATIENTS` / `DOCTORS` 等完成账号密码校验；
- 在异常情况下保证数据库资源回收与日志记录。

后续若在项目中引入 token 鉴权、密码哈希、审计日志等能力，优先推荐在该模块中进行扩展和改造。