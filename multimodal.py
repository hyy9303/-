# --- START OF FILE app/api/multimodal.py ---
import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.utils.db import get_db_connection

multimodal_bp = Blueprint('multimodal', __name__)
logger = logging.getLogger(__name__)

# 上传文件的根目录
UPLOAD_ROOT = "uploaded_files"
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# 1. 获取多模态数据列表
@multimodal_bp.route('/api/multimodal', methods=['GET'])
def get_multimodal_list():
    conn = None
    cursor = None
    try:
        modality = request.args.get('modality')
        patient_id = request.args.get('patientId')

        logger.info("Request to get multimodal list, modality=%s, patientId=%s",
                    modality, patient_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = "SELECT * FROM multimodal_data WHERE 1=1"
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
                "filePath": row["file_path"],
                "fileFormat": row["file_format"],
                "description": row["description"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None
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


# 2. 创建多模态数据
@multimodal_bp.route('/api/multimodal', methods=['POST'])
def create_multimodal():
    conn = None
    cursor = None
    try:
        form = request.form
        uploaded_file = request.files.get("file")
        get_field = form.get

        _id = get_field("id")
        modality = get_field("modality")
        patient_id = get_field("patientId")
        record_id = get_field("recordId")
        source_table = get_field("sourceTable") or "Upload"
        source_pk = get_field("sourcePk") or _id
        text_content = get_field("textContent")
        description = get_field("description")

        logger.info("Request to create multimodal: id=%s, modality=%s", _id, modality)

        # 校验必填字段
        if not _id or not modality:
            return jsonify({"success": False, "message": "id 和 modality 为必填字段"}), 400

        # 处理文件上传
        file_path = None
        file_format = None

        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            _, ext = os.path.splitext(filename)
            file_format = ext.lstrip(".").lower()
            sub_dir = modality if modality in ["text", "image", "audio", "video", "pdf", "timeseries", "other"] else "other"
            save_dir = os.path.join(UPLOAD_ROOT, sub_dir)
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            uploaded_file.save(save_path)
            file_path = save_path.replace("\\", "/")

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO multimodal_data
            (id, patient_id, record_id, source_table, source_pk,
             modality, text_content, file_path, file_format, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql, (
            _id,
            patient_id,
            record_id,
            source_table,
            source_pk,
            modality,
            text_content,
            file_path,
            file_format,
            description
        ))
        conn.commit()

        logger.info("Multimodal record %s created successfully.", _id)

        return jsonify({
            "success": True,
            "message": "多模态数据创建成功",
            "data": {
                "id": _id,
                "filePath": file_path,
                "fileFormat": file_format
            }
        }), 201

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


# 3. 删除多模态数据
@multimodal_bp.route('/api/multimodal/<string:data_id>', methods=['DELETE'])
def delete_multimodal(data_id):
    conn = None
    cursor = None
    try:
        logger.info("Request to delete multimodal record: %s", data_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT file_path FROM multimodal_data WHERE id = %s", (data_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning("Multimodal record %s not found.", data_id)
            return jsonify({"success": False, "message": "记录不存在"}), 404

        file_path = row["file_path"]

        cursor.execute("DELETE FROM multimodal_data WHERE id = %s", (data_id,))
        if cursor.rowcount == 0:
            conn.rollback()
            logger.warning("Multimodal record %s not found when deleting.", data_id)
            return jsonify({"success": False, "message": "记录不存在或已被删除"}), 404

        conn.commit()
        logger.info("Multimodal record %s deleted from DB.", data_id)

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info("File %s deleted successfully.", file_path)
            except Exception as fe:
                logger.warning("Failed to delete file %s: %s", file_path, str(fe))

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

# --- END OF FILE app/api/multimodal.py ---
