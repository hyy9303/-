# 数据库设计：业务实体 (DATABASE_BUSINESS_ENTITIES)

**项目名称**: MedData Hub 医疗数据管理系统  
**数据库名**: `meddata_hub`

本文件详细描述系统中的“临床业务实体表”，即独立表达业务动作与业务语义的数据表。这些表属于 **核心业务过程 (Core Business Process Entities)**，用于表示真实的临床流程事件：

- 挂号（appointments）
- 病历（medical_records）

它们记录“发生了什么业务”，并被上层应用和统计模块直接使用。

---

# 1. 挂号业务实体 `appointments`

## 1.1 业务含义

`appointments` 表用于表示患者挂号这一业务动作，是临床流程的入口。

每一条记录代表：

- “谁”（patient）  
- “向哪个科室/医生”（department / doctor）  
- “在什么时间”（create_time）  
- “为了什么主诉”（description）  
- “处于什么状态”（status）

👉 它是 **业务事件表**，不是维度表，也不是关联表。

---

## 1.2 表结构（DDL）

```sql
CREATE TABLE `appointments` (
  `id` VARCHAR(50) NOT NULL,
  `patient_id` VARCHAR(45) NOT NULL,
  `department_id` VARCHAR(50) NOT NULL,
  `doctor_id` VARCHAR(50) NOT NULL,
  `description` TEXT(1024) NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `create_time` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_UNIQUE` (`id`)
);

ALTER TABLE `appointments`
  ADD CONSTRAINT `fk_appt_patient`
    FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_appt_doctor`
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_appt_department`
    FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE;
```

---

## 1.3 字段说明

| 字段名        | 类型         | 说明 |
|---------------|--------------|-------|
| id            | VARCHAR(50)  | 挂号唯一标识 |
| patient_id    | VARCHAR(45)  | 患者实体（业务主角） |
| department_id | VARCHAR(50)  | 挂号进入的科室 |
| doctor_id     | VARCHAR(50)  | 分配的接诊医生 |
| description   | TEXT(1024)   | 主诉、症状描述 |
| status        | VARCHAR(20)  | 状态：pending/confirmed/cancelled |
| create_time   | VARCHAR(50)  | 创建时间（字符串） |

---

## 1.4 业务行为说明

**业务角色：**
- 患者：发起挂号
- 系统：可自动分配医生（负载均衡）
- 医生：查看“我的今日挂号队列”

**关键业务规则：**
- 一个患者可有多个挂号
- 挂号状态机通常可设计为：
  - pending（等待确认）
  - confirmed（已确认/正在就诊）
  - cancelled（已取消）

**系统使用点：**
- `/api/appointment/create`：创建挂号
- `/api/appointment/list`：按患者/医生查询
- 统计：用于 Sankey 流向（患者 → 科室 → 医生）

---

# 2. 病历业务实体 `medical_records`

## 2.1 业务含义

`medical_records` 表表示一次实际的诊疗行为，是临床流程的核心业务事件。

每条记录包含：

- 患者  
- 医生  
- 诊断结果  
- 治疗方案  
- 就诊日期  

👉 它是“就诊行为本身”的业务实体。

---

## 2.2 表结构（DDL）

```sql
CREATE TABLE `medical_records` (
  `id` VARCHAR(50) NOT NULL,
  `patient_id` VARCHAR(50) NOT NULL,
  `doctor_id` VARCHAR(50) NOT NULL,
  `diagnosis` TEXT(1024) NOT NULL,
  `treatment_plan` TEXT(1024) NOT NULL,
  `visit_date` DATE NOT NULL,
  PRIMARY KEY (`id`)
);

ALTER TABLE `medical_records`
  ADD CONSTRAINT `fk_record_patient`
    FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_record_doctor`
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE;
```

---

## 2.3 字段说明

| 字段名         | 类型         | 说明 |
|----------------|--------------|-------|
| id             | VARCHAR(50)  | 病历唯一标识 |
| patient_id     | VARCHAR(50)  | 就诊的患者 |
| doctor_id      | VARCHAR(50)  | 接诊医生 |
| diagnosis      | TEXT(1024)   | 诊断结论 |
| treatment_plan | TEXT(1024)   | 治疗方案、用药方案（不含明细） |
| visit_date     | DATE         | 就诊日期 |

---

## 2.4 业务行为说明

**业务角色：**
- 医生在看诊时创建病历
- 病历可能包含处方（由关联实体 `prescription_details` 表表达）
- 病历可挂载多模态数据（检查 PDF、影像、音频等）

**关键业务规则：**
- 一次挂号通常对应 **0 或 1 条病历**
- 病历是所有临床分析、查询、统计的重要基础
- 删除病历会级联删除处方明细（见关联实体文档）

**系统使用点：**
- `/api/record/create`：创建病历（含事务）
- `/api/record/detail`：查询病历详情
- `/api/stats/sankey`：生成患者→科室→医生就诊流向图

---

# 3. 业务实体之间的关系（不含关联表）

```text
patients ─────────→ appointments ─────────→ medical_records
             (挂号)                   (诊疗行为)
```

解释：

- 患者首先进行挂号（appointments）
- 医生根据挂号进行诊疗并形成病历（medical_records）

两者都是 **表示独立业务事件的实体**，不存在 M:N 或 R:N 的结构，因此归类为“业务实体”。

---

# 4. 业务实体与系统模块对应关系

| 模块文件 | 涉及业务实体 |
|----------|----------------|
| `appointment.py` | appointments |
| `record.py` | medical_records |
| `patient.py` | 间接引用（查询） |
| `doctor.py` | 间接引用（查询） |
| `stats.py` | appointments / medical_records |

---

# 5. 业务实体设计总结

业务实体用于描述系统中发生的关键业务事件：

1. **appointments**：代表患者“想要就诊”
2. **medical_records**：代表医生“完成了诊疗并给出诊断”

它们：

- 是系统最核心的数据表之一  
- 承载了工作流流转  
- 驱动着统计分析、多模态数据挂载、处方生成等后续行为  

关联实体（如处方明细）将在另一份独立文档中说明。


---

