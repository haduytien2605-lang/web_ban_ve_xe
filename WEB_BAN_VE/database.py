import pyodbc

def get_db_connection():
    # Chuỗi kết nối dựa trên thông tin máy của bạn
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-LJ65EG7;'
        'DATABASE= banvexekhach;' # Thay tên DB thực tế của bạn vào đây
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