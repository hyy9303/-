# 数据库设计：核心实体 (DATABASE_CORE_ENTITIES)

**项目名称**: MedData Hub 医疗数据管理系统  
**数据库名**: `meddata_hub`  

本文件详细说明系统中的核心主数据表结构与设计意图，涵盖：

- `departments` — 科室信息
- `doctors` — 医生信息
- `patients` — 患者信息
- `medicines` — 药品信息

这些表为挂号、病历、处方、多模态数据等业务表提供基础维度支撑。

---

## 1. 科室表 `departments`

### 1.1 业务含义

`departments` 用于记录医院内部的各个科室信息，是医生、挂号、就诊等模块的基础维度。

- 每条记录表示一个独立科室。
- 被医生 (`doctors`)、挂号记录 (`appointments`) 等表通过外键引用。

### 1.2 表结构（DDL）

```sql
CREATE TABLE `meddata_hub`.`departments` (
  `id` VARCHAR(50) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `location` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
  UNIQUE INDEX `name_UNIQUE` (`name` ASC) VISIBLE
);
```

### 1.3 字段说明

| 字段名    | 类型         | 约束                          | 说明                             |
|----------|--------------|-------------------------------|----------------------------------|
| id       | VARCHAR(50)  | PK, NOT NULL, UNIQUE          | 科室主键，业务唯一 ID            |
| name     | VARCHAR(100) | NOT NULL, UNIQUE              | 科室名称，如“心内科”“骨科”等    |
| location | VARCHAR(100) | NOT NULL                      | 科室所在位置，如“门诊楼 3 楼”    |

### 1.4 关系与约束

- 被以下表作为外键引用（通过其它表的 `ALTER TABLE` 定义）：
  - `doctors.department_id`
  - `appointments.department_id`
- 唯一约束 `name_UNIQUE` 保证科室名称不重复，避免出现多个同名科室。
- 在业务上用作：
  - 科室列表展示
  - 医生选择/挂号时的科室筛选条件
  - 统计分析中作为就诊流向的维度节点之一

---

## 2. 医生表 `doctors`

### 2.1 业务含义

`doctors` 用于存储医生的基本信息和账号信息，是挂号、病历、多模态数据等业务的核心参与者之一。

- 每条记录表示一位医生。
- 关联所属科室 (`departments`)。
- 同时承担“系统登录用户”的角色之一（与 `auth` 模块对接）。

### 2.2 表结构（DDL）

```sql
CREATE TABLE `meddata_hub`.`doctors` (
  `id` VARCHAR(50) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `password` VARCHAR(255) NOT NULL DEFAULT '123456',
  `title` VARCHAR(50) NOT NULL,
  `specialty` VARCHAR(100) NOT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `department_id` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
);

ALTER TABLE `meddata_hub`.`doctors` 
ADD CONSTRAINT `fk_doctor_dept`
  FOREIGN KEY (`department_id`)
  REFERENCES `meddata_hub`.`departments` (`id`)
  ON DELETE RESTRICT
  ON UPDATE CASCADE;
```

### 2.3 字段说明

| 字段名         | 类型           | 约束                               | 说明                                      |
|----------------|----------------|------------------------------------|-------------------------------------------|
| id             | VARCHAR(50)    | PK, NOT NULL, UNIQUE               | 医生唯一 ID                               |
| name           | VARCHAR(100)   | NOT NULL                           | 医生姓名                                  |
| password       | VARCHAR(255)   | NOT NULL, 默认 `'123456'`          | 登录密码（建议业务层做加密存储）          |
| title          | VARCHAR(50)    | NOT NULL                           | 职称，如“主任医师”“主治医师”等          |
| specialty      | VARCHAR(100)   | NOT NULL                           | 专业方向，如“心血管内科”“神经外科”等    |
| phone          | VARCHAR(20)    | NOT NULL                           | 联系电话                                  |
| department_id  | VARCHAR(50)    | NOT NULL, FK → `departments.id`   | 所属科室                                  |

### 2.4 关系与约束

- 与 `departments` 的关系：
  - 多个医生属于一个科室（N:1）。
  - 外键 `fk_doctor_dept`：
    - `ON DELETE RESTRICT`：不允许删除仍有医生挂靠的科室；
    - `ON UPDATE CASCADE`：科室 ID 变更会自动级联更新医生记录。
- 被以下表作为外键引用：
  - `appointments.doctor_id`（挂号记录中的接诊医生）
  - `medical_records.doctor_id`（病历记录中的接诊医生）
- 在业务上用作：
  - 登录鉴权（`auth.py`）
  - 医生信息维护（`doctor.py`）
  - 挂号/排班及负载均衡（`appointment.py`）
  - 病历记录关联（`record.py`）
  - 统计分析（`stats.py`，如医生接诊量）

---

## 3. 患者表 `patients`

### 3.1 业务含义

`patients` 用于存储患者的基础信息和账号信息，是系统中最核心的主体之一。

- 每条记录表示一名患者。
- 被挂号记录、病历、多模态数据等强关联。

### 3.2 表结构（DDL）

```sql
CREATE TABLE `meddata_hub`.`patients` (
  `id` VARCHAR(50) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `password` VARCHAR(255) NOT NULL DEFAULT '123456',
  `gender` VARCHAR(10) NOT NULL,
  `age` INT NOT NULL,
  `phone` VARCHAR(20) NULL,
  `address` VARCHAR(255) NULL,
  `create_time` DATE NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
);
```

### 3.3 字段说明

| 字段名      | 类型           | 约束                         | 说明                                              |
|------------|----------------|------------------------------|---------------------------------------------------|
| id         | VARCHAR(50)    | PK, NOT NULL, UNIQUE         | 患者唯一 ID                                       |
| name       | VARCHAR(100)   | NOT NULL                     | 患者姓名                                          |
| password   | VARCHAR(255)   | NOT NULL, 默认 `'123456'`    | 登录密码（建议业务层加密）                        |
| gender     | VARCHAR(10)    | NOT NULL                     | 性别，如 `'男'` / `'女'`（也可扩展其它值）        |
| age        | INT            | NOT NULL                     | 年龄                                              |
| phone      | VARCHAR(20)    | NULL                         | 联系电话                                          |
| address    | VARCHAR(255)   | NULL                         | 联系地址                                          |
| create_time| DATE           | NOT NULL                     | 建档/注册日期                                     |

### 3.4 关系与使用场景

- 被以下表作为外键引用（在相应表的 `ALTER TABLE` 中定义）：
  - `appointments.patient_id`
  - `medical_records.patient_id`
  - `multimodal_data.patient_id`
- 主要业务场景：
  - 患者注册与登录（`auth.py` / `patient.py`）
  - 查询患者基本信息与历史就诊记录
  - 与多模态文件绑定（如某患者的长期生命体征 CSV、音频记录等）
  - 统计分析：按患者维度统计就诊次数、不同模态文件数量等

---

## 4. 药品表 `medicines`

### 4.1 业务含义

`medicines` 用于记录医院药房中的药品信息，包括基本属性、价格及库存量，是处方明细的关键维度。

- 每条记录表示一种药品。
- 与处方明细 (`prescription_details`) 构成一对多关系。

### 4.2 表结构（DDL）

```sql
CREATE TABLE `meddata_hub`.`medicines` (
  `id` VARCHAR(50) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `price` DECIMAL(10,2) NOT NULL,
  `stock` INT NOT NULL,
  `specification` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
);
```

### 4.3 字段说明

| 字段名        | 类型            | 约束                        | 说明                                         |
|--------------|-----------------|-----------------------------|----------------------------------------------|
| id           | VARCHAR(50)     | PK, NOT NULL, UNIQUE        | 药品唯一 ID                                  |
| name         | VARCHAR(100)    | NOT NULL                    | 药品名称                                     |
| price        | DECIMAL(10,2)   | NOT NULL                    | 单价（精确到分）                             |
| stock        | INT             | NOT NULL                    | 当前库存数量                                 |
| specification| VARCHAR(100)    | NOT NULL                    | 规格，如“0.25g\*24 片/盒”“100ml/瓶”等      |

### 4.4 关系与使用场景

- 被以下表作为外键引用：
  - `prescription_details.medicine_id`
- 与业务模块的对应关系：
  - 由 `record.py` 在开具处方时读取药品信息并扣减库存。
  - 可由 `basic.py` 提供药品基础数据查询接口（如药品列表、模糊搜索）。
- 常见查询/操作：
  - 检查库存是否足够开具处方。
  - 按价格或名称排序显示。
  - 库存预警。

---

## 5. 核心实体间关系小结

从 E-R 模型角度看，这四张核心表之间的关系如下：

- `departments` ←→ `doctors`：一对多（一个科室有多名医生）
- `patients`：独立核心实体，被挂号、病历、多模态数据等多处引用
- `medicines`：独立维度表，通过 `prescription_details` 与 `medical_records` 建立联系

它们共同构成：

- 医疗业务主线：患者 (`patients`) 找医生 (`doctors`) 在科室 (`departments`) 就诊并产生处方中的药品 (`medicines`)；
- 为其它业务表（`appointments`, `medical_records`, `prescription_details`, `multimodal_data`）提供稳定的维度支撑和引用锚点。



