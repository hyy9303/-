# crud_demo.py
"""
针对 meddata_hub 数据库的 8 张表（7 张主表 + 1 张多模态表）实现：
- 每张表：增 / 删 / 查 三种功能
- 通过 main 里的注释控制当前要演示的表和操作
"""

from db_utils import get_connection


# =========================
# 1. departments 科室表
# =========================

def add_department(id, name, location=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = "INSERT INTO departments (id, name, location) VALUES (%s, %s, %s)"
    cur.execute(sql, (id, name, location))
    conn.commit()
    cur.close()
    conn.close()


def delete_department(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM departments WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_departments():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM departments")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 2. doctors 医生表
# =========================

def add_doctor(id, name, password="123456", department_id=None,
               title=None, specialty=None, phone=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO doctors (id, name, password, department_id, title, specialty, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cur.execute(sql, (id, name, password, department_id, title, specialty, phone))
    conn.commit()
    cur.close()
    conn.close()


def delete_doctor(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM doctors WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_doctors():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM doctors")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 3. medicines 药品表
# =========================

def add_medicine(id, name, price, stock, specification=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO medicines (id, name, price, stock, specification)
        VALUES (%s, %s, %s, %s, %s)
    """
    cur.execute(sql, (id, name, price, stock, specification))
    conn.commit()
    cur.close()
    conn.close()


def delete_medicine(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_medicines():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM medicines")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 4. patients 患者表
# =========================

def add_patient(id, name, password="123456",
                gender=None, age=None, phone=None, address=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO patients (id, name, password, gender, age, phone, address, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE())
    """
    cur.execute(sql, (id, name, password, gender, age, phone, address))
    conn.commit()
    cur.close()
    conn.close()


def delete_patient(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM patients WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_patients():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM patients")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 5. medical_records 病历主表
# =========================

def add_medical_record(id, patient_id, doctor_id,
                       diagnosis=None, treatment_plan=None, visit_date=None):
    
   
    
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO medical_records
        (id, patient_id, doctor_id, diagnosis, treatment_plan, visit_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cur.execute(sql, (id, patient_id, doctor_id, diagnosis, treatment_plan, visit_date))
    conn.commit()
    cur.close()
    conn.close()


def delete_medical_record(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM medical_records WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_medical_records():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM medical_records")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 6. prescription_details 处方明细表
# =========================

def add_prescription_detail(id, record_id, medicine_id,
                            dosage=None, usage_info=None, days=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO prescription_details
        (id, record_id, medicine_id, dosage, usage_info, days)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cur.execute(sql, (id, record_id, medicine_id, dosage, usage_info, days))
    conn.commit()
    cur.close()
    conn.close()


def delete_prescription_detail(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM prescription_details WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_prescription_details():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM prescription_details")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 7. appointments 挂号表
# =========================

def add_appointment(id, patient_name, patient_phone,
                    age=None, gender=None, department_id=None, doctor_id=None,
                    description=None, status=None, create_time=None):

    conn = get_connection()
    cur = conn.cursor()

    if create_time is None:
        # MySQL 端用 NOW() 生成字符串时间
        sql = """
            INSERT INTO appointments
            (id, patient_name, patient_phone, age, gender,
             department_id, doctor_id, description, status, create_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        params = (id, patient_name, patient_phone, age, gender,
                  department_id, doctor_id, description, status)
    else:
        sql = """
            INSERT INTO appointments
            (id, patient_name, patient_phone, age, gender,
             department_id, doctor_id, description, status, create_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (id, patient_name, patient_phone, age, gender,
                  department_id, doctor_id, description, status, create_time)

    cur.execute(sql, params)
    conn.commit()
    cur.close()
    conn.close()


def delete_appointment(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_appointments():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM appointments")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# 8. multimodal_data 多模态表
# =========================

def add_multimodal(id, modality, source_table, source_pk,
                   file_path=None, file_format=None,
                   patient_id=None, record_id=None,
                   text_content=None, description=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO multimodal_data
        (id, patient_id, record_id, source_table, source_pk,
         modality, text_content, file_path, file_format, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cur.execute(sql, (id, patient_id, record_id, source_table, source_pk,
                      modality, text_content, file_path, file_format, description))
    conn.commit()
    cur.close()
    conn.close()


def delete_multimodal(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM multimodal_data WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()


def get_multimodal():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM multimodal_data")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# =========================
# main：通过注释选择要演示的表和操作
# =========================

if __name__ == "__main__":
    # 下面是每一张表的示例操作
    # 想看哪张表的增/删/查，就把对应 block 的注释去掉即可

    # ---------- 1. departments ----------
    # add_department("dept1", "心内科", "一号楼3层")
    #add_department("dept2", "骨科", "二号楼5层")
    #delete_department("dept2")
    #print("所有科室：", get_departments())


    # ---------- 2. doctors ----------
    #add_doctor("doc1", "张三", department_id="dept1",title="主任医师", specialty="心血管", phone="13800000000")
    #delete_doctor("D001")
    #print("所有医生：", get_doctors())
    

    # ---------- 3. medicines ----------
    #add_medicine("med1", "阿司匹林", 12.50, 100, "100mg*20片")
    #add_medicine("med2", "布洛芬", 20.00, 50, "0.3g*24粒")
    #delete_medicine("med2")
    #print("所有药品：", get_medicines())


    # ---------- 4. patients ----------
    # add_patient("p1", "李四", gender="男", age=45,
    #             phone="13900000000", address="某某小区")
    #add_patient("p2", "王五", gender="女", age=30)
    #delete_patient("p2")
    #print("所有患者：", get_patients())

    # ---------- 5. medical_records ----------
    #add_medical_record("mr1", patient_id="p1", doctor_id="doc1",diagnosis="高血压", treatment_plan="低盐饮食+药物治疗",visit_date="2025-01-01")
    #delete_medical_record("mr1")
    #print("所有病历：", get_medical_records())

    # ---------- 6. prescription_details ----------
    #add_prescription_detail("pre1", record_id="mr1", medicine_id="med1",dosage="1片", usage_info="每日三次", days=7)
    #delete_prescription_detail("pre1")
    #print("所有处方明细：", get_prescription_details())

    # ---------- 7. appointments ----------
    #add_appointment("ap1", patient_name="赵六", patient_phone="13700000000",age=50, gender="男", department_id="dept1", doctor_id="doc1",description="胸闷胸痛一周", status="待就诊")
    #delete_appointment("ap1")
    #print("所有挂号记录：", get_appointments())

    # ---------- 8. multimodal_data ----------
    #add_multimodal(id="demo_img_1",modality="image",source_table="MedicalImage",source_pk="CTImage1",file_path="medicaldata/MedicalImage/CTImage1.jpg",file_format="jpg",description="CT 影像示例（通过代码插入）")
    delete_multimodal("demo_img_1")
    print("当前多模态记录数量：", len(get_multimodal()))

    #print("crud_demo.py 运行结束（请按需要取消注释对应部分来测试各表的增删查功能）")
