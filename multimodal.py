# --- START OF FILE app/api/multimodal.py ---
import os
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from app.utils.db import get_db_connection

multimodal_bp = Blueprint('multimodal', __name__)
logger = logging.getLogger(__name__)

# 上传文件根目录（相对项目根目录）
# 实际路径类似：E:\backend重构\uploaded_files
UPLOAD_ROOT = os.path.join(os.getcwd(), "uploaded_files")
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# 1. 获取多模态数据列表
#    GET /api/multimodal?modality=image&patientId=P001
@multimodal_bp.route('/api/multimodal', methods=['GET'])
def get_multimodal_list():
    conn = None
    cursor = None
    try:
        modality = request.args.get('modality')
        patient_id = request.args.get('patientId')

        logger.info(
            "Request to get multimodal list, modality=%s, patientId=%s",
            modality, patient_id
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT id, patient_id, record_id, source_table, source_pk,
                   modality, text_content, file_path, file_format,
                   description, created_at
            FROM multimodal_data
            WHERE 1=1
        """
        params = []

        if modality:
            sql += " AND modality = %s"
            params.append(modality)
        if patient_id:
            sql += " AND patient_id = %s"
            params.append(patient_id)

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row["id"],
                "patientId": row["patient_id"],
                "recordId": row["record_id"],
                "sourceTable": row["source_table"],
                "sourcePk": row["source_pk"],
                "modality": row["modality"],
                "textContent": row["text_content"],
                "filePath": row["file_path"],      # 相对路径：uploaded_files/...
                "fileFormat": row["file_format"],
                "description": row["description"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                # 给前端一个现成可用的文件 URL
                "fileUrl": f"/api/multimodal/file/{row['id']}",
            })

        logger.info("Fetched %d multimodal records.", len(data))
        return jsonify(data)

    except Exception as e:
        logger.error("Error occurred while fetching multimodal data: %s", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed for multimodal list.")


# 2. 创建多模态数据（支持 multipart/form-data 上传文件，也支持纯 JSON）
#    POST /api/multimodal
@multimodal_bp.route('/api/multimodal', methods=['POST'])
def create_multimodal():
    conn = None
    cursor = None
    try:
        content_type = request.content_type or ""
        is_multipart = "multipart/form-data" in content_type

        if is_multipart:
            form = request.form
            uploaded_file = request.files.get("file")
            get_field = form.get
        else:
            json_data = request.get_json(silent=True) or {}
            uploaded_file = None
            get_field = json_data.get

        _id = get_field("id")
        modality = get_field("modality")
        patient_id = get_field("patientId")
        record_id = get_field("recordId")
        source_table = get_field("sourceTable")
        source_pk = get_field("sourcePk")
        text_content = get_field("textContent")
        description = get_field("description")

        logger.info("Request to create multimodal: id=%s, modality=%s", _id, modality)

        # 必填校验
        if not _id or not modality:
            return jsonify({"success": False, "message": "id 和 modality 为必填字段"}), 400

        # 默认值，避免 NOT NULL 报错
        if not source_table:
            source_table = "Upload"
        if not source_pk:
            source_pk = _id

        # 处理文件
        file_path = None       # 存到数据库的相对路径
        file_format = None

        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            _, ext = os.path.splitext(filename)
            file_format = ext.lstrip(".").lower() if ext else None

            # 按模态分子目录，如：uploaded_files/image
            sub_dir = (
                modality
                if modality in ["text", "image", "audio", "video", "pdf", "timeseries", "other"]
                else "other"
            )
            save_dir = os.path.join(UPLOAD_ROOT, sub_dir)
            os.makedirs(save_dir, exist_ok=True)

            save_path = os.path.join(save_dir, filename)
            uploaded_file.save(save_path)

            # 存数据库用相对路径，相对于项目根目录
            # 例如：uploaded_files/image/test.jpg
            rel_path = os.path.relpath(save_path, os.getcwd()).replace("\\", "/")
            file_path = rel_path
        else:
            # 若无文件，允许直接传已有路径
            file_path = get_field("filePath")
            file_format = get_field("fileFormat")

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO multimodal_data
            (id, patient_id, record_id, source_table, source_pk,
             modality, text_content, file_path, file_format, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(
            sql,
            (
                _id,
                patient_id,
                record_id,
                source_table,
                source_pk,
                modality,
                text_content,
                file_path,
                file_format,
                description,
            ),
        )
        conn.commit()

        logger.info("Multimodal record %s created successfully.", _id)

        return jsonify(
            {
                "success": True,
                "message": "多模态数据创建成功",
                "data": {
                    "id": _id,
                    "filePath": file_path,
                    "fileFormat": file_format,
                    "fileUrl": f"/api/multimodal/file/{_id}",
                },
            }
        ), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Error occurred while creating multimodal data: %s", str(e))
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed for multimodal create.")


# 3. 删除多模态数据（同时尝试删除物理文件）
#    DELETE /api/multimodal/<id>
@multimodal_bp.route('/api/multimodal/<string:data_id>', methods=['DELETE'])
def delete_multimodal(data_id):
    conn = None
    cursor = None
    try:
        logger.info("Request to delete multimodal record: %s", data_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 先查文件路径（相对路径）
        cursor.execute("SELECT file_path FROM multimodal_data WHERE id = %s", (data_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning("Multimodal record %s not found.", data_id)
            return jsonify({"success": False, "message": "记录不存在"}), 404

        file_path = row["file_path"]

        # 删记录
        cursor.execute("DELETE FROM multimodal_data WHERE id = %s", (data_id,))
        if cursor.rowcount == 0:
            conn.rollback()
            logger.warning("Multimodal record %s not found when deleting.", data_id)
            return jsonify({"success": False, "message": "记录不存在或已被删除"}), 404

        conn.commit()
        logger.info("Multimodal record %s deleted from DB.", data_id)

        # 尝试删文件（失败也不影响记录已删）
        if file_path:
            if os.path.isabs(file_path):
                abs_path = file_path
            else:
                abs_path = os.path.join(os.getcwd(), file_path)
            abs_path = os.path.normpath(abs_path)

            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                    logger.info("File %s deleted successfully.", abs_path)
                except Exception as fe:
                    logger.warning("Failed to delete file %s: %s", abs_path, str(fe))

        return jsonify({"success": True, "message": "多模态记录及文件删除成功"}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Error deleting multimodal %s: %s", data_id, str(e))
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed for multimodal delete.")


# 4. 按 id 获取具体文件内容
#    GET /api/multimodal/file/<id>
@multimodal_bp.route('/api/multimodal/file/<string:data_id>', methods=['GET'])
def get_multimodal_file(data_id):
    conn = None
    cursor = None
    try:
        logger.info("Request to get file for multimodal record: %s", data_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT file_path FROM multimodal_data WHERE id = %s", (data_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning("Multimodal record %s not found.", data_id)
            return jsonify({"success": False, "message": "记录不存在"}), 404

        file_path = row["file_path"]
        if not file_path:
            logger.warning("Multimodal record %s has no file_path.", data_id)
            return jsonify({"success": False, "message": "该记录没有关联文件"}), 404

        # 相对路径 -> 绝对路径
        if os.path.isabs(file_path):
            abs_path = file_path
        else:
            abs_path = os.path.join(os.getcwd(), file_path)
        abs_path = os.path.normpath(abs_path)

        logger.info("Resolved file absolute path: %s", abs_path)

        if not os.path.exists(abs_path):
            logger.warning("File %s not found on disk.", abs_path)
            return jsonify({"success": False, "message": "文件不存在"}), 404

        # 直接根据绝对路径返回文件
        return send_file(abs_path, as_attachment=False)

    except Exception as e:
        logger.error("Error fetching file for multimodal %s: %s", data_id, str(e))
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed for multimodal file fetch.")

# --- END OF FILE app/api/multimodal.py ---
