# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from db_utils import get_connection
from werkzeug.utils import secure_filename
import os

# Flask 应用，当前目录作为静态目录（便于前端访问文件）
app = Flask(__name__, static_folder=".", static_url_path="/")
CORS(app)

# 上传文件统一存放目录（在后端根目录下自动创建）
UPLOAD_ROOT = "uploaded_files"
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# 统一响应封装
def ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data})


def error(message="error", code=1):
    return jsonify({"code": code, "message": message, "data": None})


# =========================
# 1. departments 科室
# =========================

@app.get("/api/departments")
def list_departments():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM departments")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/departments")
def create_department():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = "INSERT INTO departments (id, name, location) VALUES (%s, %s, %s)"
    cur.execute(sql, (data.get("id"), data.get("name"), data.get("location")))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/departments/<dept_id>")
def delete_department(dept_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM departments WHERE id=%s", (dept_id,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 2. doctors 医生
# =========================

@app.get("/api/doctors")
def list_doctors():
    department_id = request.args.get("departmentId")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if department_id:
        cur.execute(
            "SELECT id, name, department_id, title, specialty, phone "
            "FROM doctors WHERE department_id=%s",
            (department_id,),
        )
    else:
        cur.execute("SELECT id, name, department_id, title, specialty, phone FROM doctors")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/doctors")
def create_doctor():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO doctors (id, name, password, department_id, title, specialty, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("name"),
            data.get("password", "123456"),
            data.get("departmentId"),
            data.get("title"),
            data.get("specialty"),
            data.get("phone"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/doctors/<doc_id>")
def delete_doctor(doc_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM doctors WHERE id=%s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 3. medicines 药品
# =========================

@app.get("/api/medicines")
def list_medicines():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM medicines")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/medicines")
def create_medicine():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO medicines (id, name, price, stock, specification)
        VALUES (%s, %s, %s, %s, %s)
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("name"),
            data.get("price"),
            data.get("stock"),
            data.get("specification"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/medicines/<med_id>")
def delete_medicine(med_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id=%s", (med_id,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 4. patients 患者
# =========================

@app.get("/api/patients")
def list_patients():
    name_kw = request.args.get("name")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if name_kw:
        cur.execute(
            "SELECT id, name, gender, age, phone, address, create_time "
            "FROM patients WHERE name LIKE %s",
            (f"%{name_kw}%",),
        )
    else:
        cur.execute("SELECT id, name, gender, age, phone, address, create_time FROM patients")
    rows = cur.fetchall()
    for r in rows:
        r["createTime"] = r.pop("create_time")
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/patients")
def create_patient():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO patients (id, name, password, gender, age, phone, address, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE())
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("name"),
            data.get("password", "123456"),
            data.get("gender"),
            data.get("age"),
            data.get("phone"),
            data.get("address"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/patients/<pid>")
def delete_patient(pid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM patients WHERE id=%s", (pid,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 5. medical_records 病历
# =========================

@app.get("/api/medical-records")
def list_medical_records():
    patient_id = request.args.get("patientId")
    doctor_id = request.args.get("doctorId")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    sql = "SELECT * FROM medical_records WHERE 1=1"
    params = []
    if patient_id:
        sql += " AND patient_id=%s"
        params.append(patient_id)
    if doctor_id:
        sql += " AND doctor_id=%s"
        params.append(doctor_id)
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    for r in rows:
        r["patientId"] = r.pop("patient_id")
        r["doctorId"] = r.pop("doctor_id")
        r["treatmentPlan"] = r.pop("treatment_plan")
        r["visitDate"] = r.pop("visit_date")
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/medical-records")
def create_medical_record():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO medical_records
        (id, patient_id, doctor_id, diagnosis, treatment_plan, visit_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("patientId"),
            data.get("doctorId"),
            data.get("diagnosis"),
            data.get("treatmentPlan"),
            data.get("visitDate"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/medical-records/<mrid>")
def delete_medical_record(mrid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM medical_records WHERE id=%s", (mrid,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 6. prescription_details 处方明细
# =========================

@app.get("/api/prescriptions")
def list_prescriptions():
    record_id = request.args.get("recordId")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if record_id:
        cur.execute("SELECT * FROM prescription_details WHERE record_id=%s", (record_id,))
    else:
        cur.execute("SELECT * FROM prescription_details")
    rows = cur.fetchall()
    for r in rows:
        r["recordId"] = r.pop("record_id")
        r["medicineId"] = r.pop("medicine_id")
        r["usageInfo"] = r.pop("usage_info")
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/prescriptions")
def create_prescription():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO prescription_details
        (id, record_id, medicine_id, dosage, usage_info, days)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("recordId"),
            data.get("medicineId"),
            data.get("dosage"),
            data.get("usageInfo"),
            data.get("days"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/prescriptions/<preid>")
def delete_prescription(preid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM prescription_details WHERE id=%s", (preid,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 7. appointments 挂号
# =========================

@app.get("/api/appointments")
def list_appointments():
    status = request.args.get("status")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if status:
        cur.execute("SELECT * FROM appointments WHERE status=%s", (status,))
    else:
        cur.execute("SELECT * FROM appointments")
    rows = cur.fetchall()
    for r in rows:
        r["patientName"] = r.pop("patient_name")
        r["patientPhone"] = r.pop("patient_phone")
        r["departmentId"] = r.pop("department_id")
        r["doctorId"] = r.pop("doctor_id")
        r["createTime"] = r.pop("create_time")
    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/appointments")
def create_appointment():
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO appointments
        (id, patient_name, patient_phone, age, gender,
         department_id, doctor_id, description, status, create_time)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cur.execute(
        sql,
        (
            data.get("id"),
            data.get("patientName"),
            data.get("patientPhone"),
            data.get("age"),
            data.get("gender"),
            data.get("departmentId"),
            data.get("doctorId"),
            data.get("description"),
            data.get("status"),
            data.get("createTime"),  
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created")


@app.delete("/api/appointments/<apid>")
def delete_appointment(apid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id=%s", (apid,))
    conn.commit()
    cur.close()
    conn.close()
    return ok(message="deleted")


# =========================
# 8. multimodal_data 多模态（支持文件上传 + 删除文件）
# =========================

@app.get("/api/multimodal")
def list_multimodal():
    modality = request.args.get("modality")
    patient_id = request.args.get("patientId")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    sql = "SELECT * FROM multimodal_data WHERE 1=1"
    params = []
    if modality:
        sql += " AND modality=%s"
        params.append(modality)
    if patient_id:
        sql += " AND patient_id=%s"
        params.append(patient_id)
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()

    for r in rows:
        r["patientId"] = r.pop("patient_id")
        r["recordId"] = r.pop("record_id")
        r["sourceTable"] = r.pop("source_table")
        r["sourcePk"] = r.pop("source_pk")
        r["textContent"] = r.pop("text_content")
        r["filePath"] = r.pop("file_path")
        r["fileFormat"] = r.pop("file_format")
        r["createdAt"] = r.pop("created_at")

    cur.close()
    conn.close()
    return ok(rows)


@app.post("/api/multimodal")
def create_multimodal():
    """
    支持 multipart/form-data 上传文件。

    前端示例字段：
    - id: "demo_img_1"
    - modality: "image" | "audio" | "video" | "pdf" | "text" | "timeseries"
    - patientId: 可选
    - recordId: 可选
    - sourceTable: 可选，用于记录来源
    - sourcePk: 可选，用于记录来源主键
    - textContent: 可选，纯文本内容
    - description: 可选
    - file: 实际文件（jpg/png/mp3/mp4/pdf/csv 等）
    """
    form = request.form
    upload_file = request.files.get("file")

    file_path = None
    file_format = None

    if upload_file:
        filename = secure_filename(upload_file.filename)
        file_format = filename.split(".")[-1].lower()
        # 保存到 uploaded_files 下
        saved_path = os.path.join(UPLOAD_ROOT, filename)
        upload_file.save(saved_path)
        file_path = saved_path  # 写入数据库的路径

    conn = get_connection()
    cur = conn.cursor()
    sql = """
        INSERT INTO multimodal_data
        (id, patient_id, record_id, source_table, source_pk,
         modality, text_content, file_path, file_format, description)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cur.execute(
        sql,
        (
            form.get("id"),
            form.get("patientId"),
            form.get("recordId"),
            form.get("sourceTable"),
            form.get("sourcePk"),
            form.get("modality"),
            form.get("textContent"),
            file_path,
            file_format,
            form.get("description"),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()
    return ok(message="created", data={"filePath": file_path})


@app.delete("/api/multimodal/<mid>")
def delete_multimodal(mid):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # 1. 查文件路径
    cur.execute("SELECT file_path FROM multimodal_data WHERE id=%s", (mid,))
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        return error("record not found", code=404)

    file_path = row["file_path"]

    # 2. 删数据库记录
    cur.execute("DELETE FROM multimodal_data WHERE id=%s", (mid,))
    conn.commit()
    cur.close()
    conn.close()

    # 3. 删真实文件
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            # 即使删文件失败，也不影响数据库记录已删除
            pass

    return ok(message="deleted file and record")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
