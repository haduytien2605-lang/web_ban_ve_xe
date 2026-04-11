from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'super_secret_premium_key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sdt = request.form.get('username')
        mk = request.form.get('password')
        conn = get_db_connection()
        if not conn:
            flash("Lỗi kết nối cơ sở dữ liệu!", "danger")
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        cursor.execute("SELECT MaTaiKhoan, HoTen, VaiTro FROM TAI_KHOAN WHERE SoDienThoai=? AND MatKhau=?", (sdt, mk))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[2]
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for('trips') if user[2] == 'client' else url_for('admin'))
        else:
            flash("Sai số điện thoại hoặc mật khẩu!", "danger")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hoten = request.form.get('hoten')
        sdt = request.form.get('sdt')
        mk = request.form.get('password')
        
        conn = get_db_connection()
        if not conn:
            flash("Lỗi kết nối cơ sở dữ liệu!", "danger")
            return redirect(url_for('register'))
            
        cursor = conn.cursor()
        
        # Kiểm tra xem SĐT đã tồn tại chưa
        cursor.execute("SELECT * FROM TAI_KHOAN WHERE SoDienThoai=?", (sdt,))
        if cursor.fetchone():
            flash("Số điện thoại này đã được đăng ký! Vui lòng dùng số khác.", "danger")
            conn.close()
            return redirect(url_for('register'))
            
        try:
            # Ghi mật khẩu và mặc định VaiTro là client
            cursor.execute("INSERT INTO TAI_KHOAN (HoTen, SoDienThoai, MatKhau, VaiTro) VALUES (?, ?, ?, 'client')", (hoten, sdt, mk))
            conn.commit()
            
            # Trích xuất lại Mã Tài Khoản tự sinh để tạo Phiên Đăng Nhập
            cursor.execute("SELECT MaTaiKhoan, HoTen, VaiTro FROM TAI_KHOAN WHERE SoDienThoai=?", (sdt,))
            new_user = cursor.fetchone()
            
            session['user_id'] = new_user[0]
            session['user_name'] = new_user[1]
            session['role'] = new_user[2]
            
            flash("Tạo tài khoản thành công! Xác thực vào đặt chuyến ngay.", "success")
            return redirect(url_for('trips'))
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi khi đăng ký: {e}", "danger")
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/trips')
def trips():
    if 'user_id' not in session: return redirect(url_for('login'))
    search = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lấy danh sách chuyến xe và số lượng ghế trống từ bảng VE_XE
    query = """
    SELECT 
        C.MaChuyen, C.DiemDi, C.DiemDen, C.ThoiGianKhoiHanh, C.GiaVe,
        (SELECT COUNT(*) FROM VE_XE V WHERE V.MaChuyen = C.MaChuyen AND V.TrangThai = N'Trống') as SoGheTrong,
        (SELECT COUNT(*) FROM VE_XE V WHERE V.MaChuyen = C.MaChuyen) as TongSoGhe
    FROM CHUYEN_XE C
    """
    
    if search:
        query += " WHERE C.DiemDi LIKE ? OR C.DiemDen LIKE ?"
        cursor.execute(query, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute(query)
        
    rows = cursor.fetchall()
    conn.close()
    
    trip_list = []
    for r in rows:
        trip_list.append({
            'MaChuyen': r[0],
            'DiemDi': r[1],
            'DiemDen': r[2],
            'ThoiGian': r[3].strftime("%H:%M - %d/%m/%Y"),
            'GiaVe': f"{int(r[4]):,} VNĐ".replace(',', '.'),
            'SoGheTrong': r[5],
            'TongSoGhe': r[6],
            'PhanTram': int(((r[6] - r[5]) / r[6] * 100)) if r[6] > 0 else 0
        })
    return render_template('trips.html', trips=trip_list)

@app.route('/seats')
def seats():
    if 'user_id' not in session: return redirect(url_for('login'))
    machuyen = request.args.get('machuyen')
    if not machuyen: return redirect(url_for('trips'))
    session['current_machuyen'] = machuyen
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MaGhe, TrangThai FROM VE_XE WHERE MaChuyen = ?", (machuyen,))
    all_seats = cursor.fetchall()
    
    # Lấy thông tin giá vé chung của chuyến
    cursor.execute("SELECT GiaVe FROM CHUYEN_XE WHERE MaChuyen = ?", (machuyen,))
    gia_ve = cursor.fetchone()[0]
    conn.close()
    
    booked_seats = [s[0].strip() for s in all_seats if s[1] != 'Trống']
    return render_template('seats.html', booked_seats=booked_seats, machuyen=machuyen, giave=gia_ve)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Xử lý Lưu Database
        machuyen = session.get('current_machuyen')
        user_id = session.get('user_id')
        ghe_str = request.form.get('ghe')
        tong_tien = float(request.form.get('tong_tien', 0))
        
        if not ghe_str or not machuyen:
            flash("Dữ liệu không hợp lệ", "danger")
            return redirect(url_for('trips'))
            
        danh_sach_ghe = [g.strip() for g in ghe_str.split(',')]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. Update trạng thái các ghế
            placeholders = ','.join(['?'] * len(danh_sach_ghe))
            update_query = f"UPDATE VE_XE SET TrangThai=N'Đã đặt', MaTaiKhoan=?, NgayDat=GETDATE() WHERE MaChuyen=? AND MaGhe IN ({placeholders})"
            params = [user_id, machuyen] + danh_sach_ghe
            cursor.execute(update_query, params)
            
            # 2. Sinh lịch sử Thanh Toán
            cursor.execute("INSERT INTO THANH_TOAN (MaTaiKhoan, SoTien, GhiChu) VALUES (?, ?, ?)", 
                           (user_id, tong_tien, f"Thanh toán vé xe chuyến {machuyen}, ghế: {ghe_str}"))
            conn.commit()
            flash("Thanh toán & Đặt vé thành công!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Có lỗi xảy ra: {e}", "danger")
        finally:
            conn.close()
            
        return redirect(url_for('success'))
    
    # GET: Hiển thị giao diện hoá đơn
    ghe_duoc_chon = request.args.get('ghe', '')
    giave = request.args.get('giave', '0')
    tongtien = float(giave) * len([g for g in ghe_duoc_chon.split(',') if g.strip()]) if ghe_duoc_chon else 0
    return render_template('payment.html', ghe=ghe_duoc_chon, tongtien=tongtien, giave=giave)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/mytickets')
def mytickets():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session.get('user_id')
    
    query = """
    SELECT 
        C.MaChuyen, C.DiemDi, C.DiemDen, C.ThoiGianKhoiHanh, 
        V.MaGhe, V.NgayDat, C.GiaVe, V.MaVe
    FROM VE_XE V
    JOIN CHUYEN_XE C ON V.MaChuyen = C.MaChuyen
    WHERE V.MaTaiKhoan = ? AND V.TrangThai = N'Đã đặt'
    ORDER BY V.NgayDat DESC
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    tickets = []
    for r in rows:
        tickets.append({
            'MaChuyen': r[0],
            'DiemDi': r[1],
            'DiemDen': r[2],
            'ThoiGian': r[3].strftime("%H:%M - %d/%m/%Y"),
            'MaGhe': r[4],
            'NgayDat': r[5].strftime("%H:%M - %d/%m/%Y") if r[5] else 'N/A',
            'GiaVe': f"{int(r[6]):,} VNĐ".replace(',', '.'),
            'MaVe': r[7]
        })
        
    return render_template('mytickets.html', tickets=tickets)

@app.route('/admin')
def admin():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Chuẩn bị điều kiện lọc cho SQL
    where_clause = ""
    params = []
    if start_date and end_date:
        # Lọc từ đầu ngày start_date đến cuối ngày end_date
        where_clause = " WHERE NgayThanhToan >= ? AND NgayThanhToan <= ?"
        params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
    
    # 1. Thống kê
    cursor.execute(f"SELECT COUNT(*), ISNULL(SUM(SoTien), 0) FROM THANH_TOAN{where_clause}", params)
    stats = cursor.fetchone()
    total_orders = stats[0]
    total_revenue = stats[1]
    
    # 2. Danh sách xe (Không bị ảnh hưởng bởi lọc ngày)
    cursor.execute("SELECT MaXe, BienSo, LoaiXe, SoGhe FROM XE")
    cars = cursor.fetchall()
    
    # 3. Danh sách chuyến xe (Hiển thị tất cả)
    cursor.execute("""
        SELECT C.MaChuyen, X.BienSo, C.DiemDi, C.DiemDen, C.ThoiGianKhoiHanh, C.GiaVe
        FROM CHUYEN_XE C
        JOIN XE X ON C.MaXe = X.MaXe
        ORDER BY C.ThoiGianKhoiHanh DESC
    """)
    trips = cursor.fetchall()
    
    # 4. Danh sách đơn hàng (Bị ảnh hưởng bởi lọc ngày)
    cursor.execute(f"""
        SELECT T.MaThanhToan, K.HoTen, T.SoTien, T.NgayThanhToan, T.GhiChu
        FROM THANH_TOAN T
        JOIN TAI_KHOAN K ON T.MaTaiKhoan = K.MaTaiKhoan
        {where_clause}
        ORDER BY T.NgayThanhToan DESC
    """, params)
    payments = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          total_orders=total_orders, 
                          total_revenue=f"{int(total_revenue):,} VNĐ".replace(',', '.'),
                          cars=cars, 
                          trips=trips,
                          payments=payments,
                          start_date=start_date,
                          end_date=end_date)

@app.route('/admin/add_car', methods=['POST'])
def add_car():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    bienso = request.form.get('bienso')
    loaixe = request.form.get('loaixe')
    soghe = 7
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO XE (BienSo, LoaiXe, SoGhe) VALUES (?, ?, ?)", (bienso, loaixe, soghe))
        conn.commit()
        flash("Thêm xe thành công!", "success")
    except Exception as e:
        flash(f"Lỗi: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_car/<int:maxe>', methods=['POST'])
def delete_car(maxe):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM XE WHERE MaXe = ?", (maxe,))
        conn.commit()
        flash("Xoá xe thành công!", "success")
    except Exception as e:
        flash("Không thể xoá xe này vì đang bị ràng buộc bởi các chuyến xe đã được tạo!", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_trip', methods=['POST'])
def add_trip():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    maxe = request.form.get('maxe')
    diemdi = request.form.get('diemdi')
    diemden = request.form.get('diemden')
    thoigian = request.form.get('thoigian').replace('T', ' ') if request.form.get('thoigian') else None
    giave = request.form.get('giave')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO CHUYEN_XE (MaXe, DiemDi, DiemDen, ThoiGianKhoiHanh, GiaVe)
            OUTPUT inserted.MaChuyen
            VALUES (?, ?, ?, ?, ?)
        """, (maxe, diemdi, diemden, thoigian, giave))
        
        machuyen = cursor.fetchone()[0]
        
        # Tự động tạo 7 ghế
        ghe_list = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B4']
        for ghe in ghe_list:
            cursor.execute("""
                INSERT INTO VE_XE (MaChuyen, MaGhe, GiaVe, TrangThai)
                VALUES (?, ?, ?, N'Trống')
            """, (machuyen, ghe, giave))
            
        conn.commit()
        flash("Thêm chuyến xe thành công. Đã tự động tạo sơ đồ 7 ghế!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi thêm chuyến: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/edit_trip/<int:machuyen>', methods=['POST'])
def edit_trip(machuyen):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    thoigian = request.form.get('thoigian').replace('T', ' ') if request.form.get('thoigian') else None
    giave = request.form.get('giave')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE CHUYEN_XE SET ThoiGianKhoiHanh = ?, GiaVe = ? WHERE MaChuyen = ?", (thoigian, giave, machuyen))
        cursor.execute("UPDATE VE_XE SET GiaVe = ? WHERE MaChuyen = ? AND TrangThai = N'Trống'", (giave, machuyen))
        conn.commit()
        flash("Cập nhật thông tin chuyến xe thành công!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/cancel_ticket/<int:mave>', methods=['POST'])
def cancel_ticket(mave):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Lấy thông tin vé để trừ tiền và tìm hóa đơn
        cursor.execute("""
            SELECT V.MaChuyen, V.MaGhe, V.GiaVe 
            FROM VE_XE V 
            WHERE V.MaVe = ? AND V.MaTaiKhoan = ? AND V.TrangThai = N'Đã đặt'
        """, (mave, user_id))
        ticket = cursor.fetchone()
        
        if not ticket:
            flash("Không tìm thấy thông tin vé hoặc vé đã được hủy!", "danger")
            return redirect(url_for('mytickets'))
            
        machuyen, maghe, giave = ticket
        
        # 2. Cập nhật vé về trạng thái Trống
        cursor.execute("UPDATE VE_XE SET TrangThai = N'Trống', MaTaiKhoan = NULL, NgayDat = NULL WHERE MaVe = ?", (mave,))
        
        # 3. Trừ doanh thu: Tìm bản ghi thanh toán có chứa mã ghế và mã chuyến này
        search_pattern = f"%chuyến {machuyen}, ghế:%{maghe}%"
        cursor.execute("SELECT MaThanhToan, SoTien FROM THANH_TOAN WHERE MaTaiKhoan = ? AND GhiChu LIKE ?", (user_id, search_pattern))
        payment = cursor.fetchone()
        
        if payment:
            path_tt, sotien_tt = payment
            new_sotien = float(sotien_tt) - float(giave)
            
            if new_sotien <= 0:
                cursor.execute("DELETE FROM THANH_TOAN WHERE MaThanhToan = ?", (path_tt,))
            else:
                cursor.execute("UPDATE THANH_TOAN SET SoTien = ? WHERE MaThanhToan = ?", (new_sotien, path_tt))
        
        conn.commit()
        flash("Hủy vé thành công! Doanh thu đã được tự động cập nhật.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi hủy vé: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('mytickets'))

@app.route('/admin/delete_trip/<int:machuyen>', methods=['POST'])
def delete_trip(machuyen):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM THANH_TOAN WHERE GhiChu LIKE ?", (f"Thanh toán vé xe chuyến {machuyen}, ghế:%",))
        cursor.execute("DELETE FROM VE_XE WHERE MaChuyen = ?", (machuyen,))
        cursor.execute("DELETE FROM CHUYEN_XE WHERE MaChuyen = ?", (machuyen,))
        conn.commit()
        flash("Đã huỷ chuyến, tự động huỷ vé và trừ doanh thu tương ứng!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi huỷ chuyến: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/reset_system', methods=['POST'])
def reset_system():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Xóa toàn bộ lịch sử thanh toán (Doanh thu)
        cursor.execute("DELETE FROM THANH_TOAN")
        
        # 2. Đưa toàn bộ các ghế đã đặt về trạng thái trống
        cursor.execute("UPDATE VE_XE SET TrangThai = N'Trống', MaTaiKhoan = NULL, NgayDat = NULL")
        
        conn.commit()
        flash("Hệ thống đã được reset! Doanh thu về 0 và toàn bộ ghế đã trống.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi reset hệ thống: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
