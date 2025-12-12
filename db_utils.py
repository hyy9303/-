# db_utils.py
import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        #host="127.0.0.1",
        host="localhost",        
        #port=3306,
        user="root",
        password="111111",  # <- 一定要改成你登录 mysql 那个密码
        database="meddata_hub",
        charset="utf8mb4",
        use_pure=True            # 避免 C 扩展的一些奇怪兼容问题
    )
    return conn
