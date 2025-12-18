# --- START OF FILE app/__init__.py ---
import logging
from flask import Flask
from flask_cors import CORS


def setup_logging():
    """配置全局日志"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 如果已经有处理器，避免重复添加
    if logger.handlers:
        return

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 文件处理器
    file_handler = logging.FileHandler('app.log', mode='a')
    file_handler.setLevel(logging.WARNING)

    # 格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def create_app():
    app = Flask(__name__)
    CORS(app)  # 允许跨域

    # 1. 初始化日志
    setup_logging()

    # 2. 注册蓝图（在此导入，避免循环依赖）
    from app.api.auth import auth_bp
    from app.api.basic import basic_bp
    from app.api.doctor import doctor_bp
    from app.api.patient import patient_bp
    from app.api.record import record_bp
    from app.api.appointment import appointment_bp
    from app.api.stats import stats_bp

    # ⭐ 新增：引入多模态模块
    from app.api.multimodal import multimodal_bp

    # 3. 注册所有蓝图
    app.register_blueprint(auth_bp)          # /api/login
    app.register_blueprint(basic_bp)         # /api/departments, /api/medicines
    app.register_blueprint(doctor_bp)        # /api/doctors
    app.register_blueprint(patient_bp)       # /api/patients
    app.register_blueprint(record_bp)        # /api/records
    app.register_blueprint(appointment_bp)   # /api/appointments
    app.register_blueprint(stats_bp)         # /api/stats

    # ⭐ 注册多模态蓝图
    app.register_blueprint(multimodal_bp)    # /api/multimodal

    @app.route('/')
    def index():
        return "MedData Hub API is running..."

    return app

# --- END OF FILE app/__init__.py ---
