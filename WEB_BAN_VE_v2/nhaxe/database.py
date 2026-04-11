import pyodbc

def get_db_connection():
    # Chuỗi kết nối đến server mới.
    # CHÚ Ý: Database đã đổi thành nhaxe_db (CSDL mới theo thiết kế chuẩn)
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-LJ65EG7;'
        'DATABASE=nhaxe_db;'
        'UID=sa;'
        'PWD=123;'
        'TrustServerCertificate=yes;'
    )
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Lỗi kết nối database: {e}")
        return None
