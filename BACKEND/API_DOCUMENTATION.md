# MedData Hub - 后端接口汇总


## 1. 认证模块

| 文件名           | 接口路径            | 操作方式 | 描述         |
| :--------------- | :------------------ | :------- | :----------- |
| `auth.py` | `/api/login` | `POST`  | 用户认证登录               |


## 2. 基础数据 

| 文件名           | 接口路径            | 操作方式 | 描述         |
| :--------------- | :------------------ | :------- | :----------- |
| `basic.py` | `/api/departments`                 | `GET`    | 获取所有科室信息                       |
| `basic.py` | `/api/departments/<department_id>` | `GET`    | 获取科室详情（包含医生数量）           |
| `basic.py` | `/api/departments/<department_id>` | `DELETE` | 删除科室（需确保医生数量为0）          |
| `basic.py` | `/api/medicines`                   | `GET`    | 获取所有药品信息                       |
| `basic.py` | `/api/medicines/<medicine_id>`     | `GET`    | 获取某个药品详情                       |
| `basic.py` | `/api/medicines/<medicine_id>`     | `PUT`    | 修改药品信息                           |
| `basic.py` | `/api/medicines/<medicine_id>`     | `DELETE` | 删除药品（若有相关处方细则则无法删除） |

## 3. 患者管理

| 文件名           | 接口路径            | 操作方式 | 描述         |
| :--------------- | :------------------ | :------- | :----------- |
| `patient.py` | `/api/patients`              | `GET`    | 获取所有患者信息（支持按ID查询和分页，标记VIP） |
| `patient.py` | `/api/patients`              | `POST`   | 新增/注册患者（包含ID存在性校验）               |
| `patient.py` | `/api/patients/<p_id>`       | `PUT`    | 更新患者信息                                    |
| `patient.py` | `/api/patients/<p_id>`       | `DELETE` | 删除患者（级联删除相关挂号和病历记录）          |
| `patient.py` | `/api/patients/count`        | `GET`    | 查询患者总数                                    |
| `patient.py` | `/api/patients/gender_ratio` | `GET`    | 患者性别比例统计                                |
| `patient.py` | `/api/patients/age_ratio`    | `GET`    | 患者年龄比例统计                                |

## 4. 医生管理

| 文件名           | 接口路径            | 操作方式 | 描述         |
| :--------------- | :------------------ | :------- | :----------- |
| `doctor.py` | `/api/doctors`             | `GET`    | 获取所有医生信息（包含待处理挂号数量）  |
| `doctor.py` | `/api/doctors/<doctor_id>` | `GET`    | 获取某个医生详情                        |
| `doctor.py` | `/api/doctors/<doctor_id>` | `PUT`    | 修改医生信息                            |
| `doctor.py` | `/api/doctors/<doctor_id>` | `DELETE` | 删除医生（若有病历/挂号关联则无法删除） |

## 5. 核心业务：挂号

| 文件名           | 接口路径                            | 操作方式 | 描述                       |
| :--------------- | :---------------------------------- | :------- | :------------------------- |
| `appointment.py` | `/api/appointments`                 | `GET`    | 获取预约数据               |
| `appointment.py` | `/api/appointments/statistics`      | `GET`    | 根据年、月、日统计预约数据 |
| `appointment.py` | `/api/appointments`                 | `POST`     | 提交挂号                   |
| `appointment.py` | `/api/appointments/<string:apt_id>` | `PUT`      | 更新挂号状态               |

## 6. 核心业务：电子病历

| 文件名           | 接口路径                            | 操作方式 | 描述                       |
| :--------------- | :---------------------------------- | :------- | :------------------------- |
| `record.py` | `/api/records`              | `GET`    | 获取所有（或某个患者）病历记录                     |
| `record.py` | `/api/prescription_details` | `GET`    | 获取所有（或某个病历）处方细则                     |
| `record.py` | `/api/records`              | `POST`   | 提交病历（包含主表和子表插入，事务处理，库存校验） |
| `record.py` | `/api/records/<record_id>`  | `DELETE` | 删除病历（级联删除处方明细）                       |

## 7.多模态数据

| 文件名           | 接口路径                            | 操作方式 | 描述                       |
| :--------------- | :---------------------------------- | :------- | :------------------------- |
| `multimodal.py` | `/api/multimodal`                       | `GET`    | 获取多模态数据列表     |
| `multimodal.py` | `/api/multimodal`                       | `POST`   | 创建多模态数据         |
| `multimodal.py` | `/api/multimodal/<string:data_id>`      | `DELETE` | 删除多模态数据         |
| `multimodal.py` | `/api/multimodal/file/<string:data_id>` | `GET`    | 按 id 获取具体文件内容 |

## 8.大数据统计

| 文件名           | 接口路径                            | 操作方式 | 描述                       |
| :--------------- | :---------------------------------- | :------- | :------------------------- |
| `stats.py` | `/api/stats/sankey`       | `GET` | 统计桑基图数据                    |
| `stats.py` | `/api/statistics/monthly` | `GET` | 按月份计算患者/就诊人数环比增长率 |

