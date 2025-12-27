# 数据库设计：关联实体 (DATABASE_RELATION_ENTITIES)

**项目名称**: MedData Hub 医疗数据管理系统  
**数据库名**: `meddata_hub`  

本文件描述系统中的 **关联实体（Relation / Bridge Entity）**，用于连接业务实体与核心实体。

本系统中唯一的纯关联实体为：

- `prescription_details` —— 用于建立 `medical_records`（病历）与 `medicines`（药品）之间的多对多关系，并存储用药明细。

多模态文件关联（`multimodal_data`）属于扩展实体，已被拆分至 **DATABASE_EXTENDED_ENTITIES.md**。

---

# 1. 处方明细关联实体 `prescription_details`

## 1.1 业务含义

`prescription_details` 表用于表示 **一次病历中开具的全部用药明细**。  
它在系统中承担：

### 1）多对多桥接关系
- 一份病历可以包含多种药品。
- 一种药品可以被多份病历引用。

因此形成了典型的 **多对多关联表 (M:N relation table)**。

### 2）处方明细（line item）
每条记录代表：

- 开了什么药（medicine）
- 用量和用法（dosage, usage_info）
- 使用多少天（days）

是处方的不可缺少的“明细层”。

---

## 1.2 表结构（DDL）

```sql
CREATE TABLE `meddata_hub`.`prescription_details` (
  `id` VARCHAR(50) NOT NULL,
  `record_id` VARCHAR(50) NOT NULL,
  `medicine_id` VARCHAR(50) NOT NULL,
  `dosage` VARCHAR(100) NOT NULL,
  `usage_info` VARCHAR(100) NOT NULL,
  `days` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
);

ALTER TABLE `meddata_hub`.`prescription_details` 
ADD CONSTRAINT `fk_detail_record`
  FOREIGN KEY (`record_id`)
  REFERENCES `meddata_hub`.`medical_records` (`id`)
  ON DELETE CASCADE,
ADD CONSTRAINT `fk_detail_medicine`
  FOREIGN KEY (`medicine_id`)
  REFERENCES `meddata_hub`.`medicines` (`id`);
```

---

## 1.3 字段说明

| 字段名       | 类型         | 说明 |
|--------------|--------------|------|
| id           | VARCHAR(50)  | 明细唯一 ID |
| record_id    | VARCHAR(50)  | 所属病历 ID（关联 `medical_records`） |
| medicine_id  | VARCHAR(50)  | 药品 ID（关联 `medicines`） |
| dosage       | VARCHAR(100) | 单次剂量，如“1 片”“5ml” |
| usage_info   | VARCHAR(100) | 用法说明，如“一日三次，饭后服用” |
| days         | INT          | 用药天数 |

---

## 1.4 关联关系与外键约束

### （1）与 `medical_records`（病历）

- 关系：一对多（1 条病历 → N 条处方明细）
- 外键：`fk_detail_record`
- `ON DELETE CASCADE`：
  - 删除病历会自动删除所有相关的处方明细
  - 防止孤立数据

### （2）与 `medicines`（药品）

- 关系：多对一（N 条明细 → 1 个药品）
- 外键：`fk_detail_medicine`
- 删除药品时不级联删除明细（符合医疗数据不允许破坏历史的原则）

---

## 1.5 在业务中的作用

处方明细属于 **诊疗事件的细节构成部分**，系统中主要用于：

- 医生开方：`record.py` 中创建病历时插入多条处方记录  
- 库存扣减：根据处方数量扣除 `medicines.stock`  
- 病历查询：前端展示用户用药详情  
- 医疗统计扩展：
  - 药品使用频率统计  
  - 某疾病对应的典型用药模式分析  

---

## 1.6 常用查询示例

### 1）查询某条病历的全部处方项

```sql
SELECT d.*, m.name AS medicine_name, m.specification
FROM prescription_details d
JOIN medicines m ON d.medicine_id = m.id
WHERE d.record_id = :record_id;
```

### 2）统计某药品被开具的次数

```sql
SELECT COUNT(*) AS usage_count
FROM prescription_details
WHERE medicine_id = :medicine_id;
```

---

# 2. 关联实体小结

`prescription_details` 是本项目中唯一的纯粹关联实体，承担以下职责：

- 将 **病历（medical_records）** 与 **药品（medicines）** 建立多对多关联  
- 承担处方明细的“行项目”角色  
- 参与库存管理与统计分析  
- 是医疗数据库中必不可少的结构性数据层  



---
