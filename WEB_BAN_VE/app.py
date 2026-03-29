from flask import Flask, render_template, url_for, request, redirect, session, flash
import pyodbc

app = Flask(__name__)
app.secret_key = 'duytien_bus_transport_secret_key'

# --- 1. HÀM KẾT NỐI DATABASE ---
def get_db_connection():
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-LJ65EG7;'
        'DATABASE=dichvudatxe;'
        'UID=sa;'
        'PWD=123;'
        'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str)

# --- 2. TRANG ĐĂNG NHẬP ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sdt = request.form.get('username') 
        matkhau = request.form.get('password')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Kiểm tra Admin
            cursor.execute("SELECT MaNhanVien, TenNhanVien FROM NHAN_VIEN WHERE SoDienThoai=? AND MatKhau=?", (sdt, matkhau))
            admin = cursor.fetchone()
            if admin:
                session['role'] = 'admin'
                session['user_id'] = admin[0]
                session['user_name'] = admin[1]
                conn.close()
                return redirect(url_for('admin_dashboard'))

            # Kiểm tra Khách hàng
            cursor.execute("SELECT MaKhachHang, TenKhachHang FROM KHACH_HANG WHERE SoDienThoai=? AND MatKhau=?", (sdt, matkhau))
            user = cursor.fetchone()
            if user:
                session['role'] = 'client'
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                conn.close()
                return redirect(url_for('index'))

            conn.close()
            return render_template('login.html', error="Số điện thoại hoặc mật khẩu không đúng!")
        except Exception as e:
            return f"Lỗi hệ thống: {e}"

    return render_template('login.html')

# --- 3. LUỒNG ADMIN ---
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(SoTien), COUNT(MaThanhToan) FROM THANH_TOAN WHERE TrangThai=N'Đã thanh toán'")
        row = cursor.fetchone()
        cursor.execute("SELECT COUNT(MaChuyen) FROM CHUYEN_XE WHERE CAST(ThoiGianKhoiHanh AS DATE) = CAST(GETDATE() AS DATE)")
        row_bus = cursor.fetchone()
        stats = {
            'doanh_thu': row[0] if row[0] else 0, 
            'so_ve_ban': row[1] if row[1] else 0,
            'chuyen_trong_ngay': row_bus[0] if row_bus[0] else 0
        }
        conn.close()
        return render_template('admin/dashboard.html', stats=stats)
    except:
        return render_template('admin/dashboard.html', stats={'doanh_thu': 0, 'so_ve_ban': 0, 'chuyen_trong_ngay': 0})

@app.route('/admin/manage-tickets')
def manage_tickets():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT CX.MaChuyen, KH.TenKhachHang, CX.MaGhe, CX.GiaVe, CX.TrangThai FROM CHUYEN_XE CX LEFT JOIN KHACH_HANG KH ON CX.MaKhachHang = KH.MaKhachHang"
    cursor.execute(query)
    tickets = cursor.fetchall()
    conn.close()
    return render_template('admin/manage_tickets.html', tickets=tickets)

# --- 4. LUỒNG KHÁCH HÀNG ---
@app.route('/index')
def index():
    if session.get('role') != 'client': return redirect(url_for('login'))
    return render_template('client/index.html')

@app.route('/pick-time')
def pick_time():
    if session.get('role') != 'client': return redirect(url_for('login'))
    return render_template('client/chon_gio_di.html')

@app.route('/seat')
def seat():
    if session.get('role') != 'client': return redirect(url_for('login'))
    
    machuyen = request.args.get('machuyen', 'CX001') 
    session['current_machuyen'] = machuyen 
    
    booked_seats = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT MaGhe FROM CHUYEN_XE WHERE MaChuyen = ? AND TrangThai <> N'Trống'"
        cursor.execute(query, (machuyen,))
        booked_seats = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"Lỗi lấy ghế: {e}")

    return render_template('client/select_seat.html', booked_seats=booked_seats, machuyen=machuyen)

@app.route('/payment')
def payment():
    if session.get('role') != 'client': return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    machuyen = session.get('current_machuyen', 'CX001')
    
    phone_number = "Chưa cập nhật"
    time_info = "Chưa xác định"
    departure = "Nghệ An"
    destination = "Hà Nội"
    price = 300000

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SoDienThoai FROM KHACH_HANG WHERE MaKhachHang = ?", (user_id,))
        row_user = cursor.fetchone()
        if row_user:
            phone_number = row_user[0]
            
        cursor.execute("SELECT ThoiGianKhoiHanh, DiemDi, DiemDen, GiaVe FROM CHUYEN_XE WHERE MaChuyen = ?", (machuyen,))
        row_chuyen = cursor.fetchone()
        if row_chuyen:
            time_info = row_chuyen[0].strftime("%H:%M - %d/%m/%Y")
            departure = row_chuyen[1]
            destination = row_chuyen[2]
            price = row_chuyen[3]

        conn.close()
    except Exception as e:
        print(f"Lỗi truy vấn dữ liệu thanh toán: {e}")

    ticket_info = {
        'nha_xe': 'VẬN TẢI DUY TIẾN',
        'hotline': '0912.999.999',
        'khach_hang': session.get('user_name'),
        'so_dt': phone_number,
        'tuyen_duong': f"{departure} - {destination}",
        'so_ghe': request.args.get('ghe', 'A1'),
        'ma_ve': f"DT-{machuyen}",
        'thoi_gian': time_info,
        'diem_len': departure,
        'diem_xuong': destination,
        'tong_tien': price
    }
    return render_template('client/xac_nhan_thanh_toan.html', ticket=ticket_info)

# --- BỔ SUNG CÁC ROUTE ACCOUNT & NOTIFICATIONS ---
@app.route('/account')
def account():
    if session.get('role') != 'client': return redirect(url_for('login'))
    return render_template('client/account.html')

@app.route('/notifications')
def notifications():
    if session.get('role') != 'client': return redirect(url_for('login'))
    return render_template('client/notifications.html')

# --- CÁC ROUTE CÒN LẠI ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)