CREATE DATABASE nhaxe_db;
GO
USE nhaxe_db;
GO

-- 1. TAI_KHOAN (Tài khoản người dùng & Admin)
CREATE TABLE TAI_KHOAN (
    MaTaiKhoan INT IDENTITY(1,1) PRIMARY KEY,
    HoTen NVARCHAR(100) NOT NULL,
    SoDienThoai VARCHAR(15) UNIQUE NOT NULL,
    MatKhau VARCHAR(50) NOT NULL,
    VaiTro VARCHAR(10) DEFAULT 'client' -- 'admin' hoặc 'client'
);

-- 2. LOAI_XE & XE (Quản lý xe ô tô)
CREATE TABLE XE (
    MaXe INT IDENTITY(1,1) PRIMARY KEY,
    BienSo VARCHAR(20) NOT NULL,
    LoaiXe NVARCHAR(50) DEFAULT N'Xe Limousine VIP',
    SoGhe INT DEFAULT 7
);

-- 3. CHUYEN_XE (Quản lý Lịch trình đi lại - Mỗi dòng 1 lịch trình)
CREATE TABLE CHUYEN_XE (
    MaChuyen INT IDENTITY(1,1) PRIMARY KEY,
    MaXe INT FOREIGN KEY REFERENCES XE(MaXe),
    DiemDi NVARCHAR(100) NOT NULL,
    DiemDen NVARCHAR(100) NOT NULL,
    ThoiGianKhoiHanh DATETIME NOT NULL,
    GiaVe FLOAT NOT NULL,
    TrangThai NVARCHAR(50) DEFAULT N'Sắp khởi hành'
);

-- 4. VE_XE (Quản lý Vé/Ghế thực tế) - Liên kết Chuyến Xe, Khách Hàng và Ghế
CREATE TABLE VE_XE (
    MaVe INT IDENTITY(1,1) PRIMARY KEY,
    MaChuyen INT NOT NULL FOREIGN KEY REFERENCES CHUYEN_XE(MaChuyen),
    MaGhe VARCHAR(5) NOT NULL, -- Ví dụ: 'A1', 'B2',
    MaTaiKhoan INT NULL FOREIGN KEY REFERENCES TAI_KHOAN(MaTaiKhoan), -- NULL nghĩa là chưa ai mua
    GiaVe FLOAT NOT NULL,
    TrangThai NVARCHAR(50) DEFAULT N'Trống', -- 'Trống', 'Đang giữ', 'Đã đặt'
    NgayDat DATETIME NULL,
    CONSTRAINT UQ_Chuyen_Ghe UNIQUE(MaChuyen, MaGhe) -- Một ghế trên 1 chuyến chỉ tồn tại 1 lần
);

-- 5. THANH_TOAN (Quản lý thu chi)
CREATE TABLE THANH_TOAN (
    MaThanhToan INT IDENTITY(1,1) PRIMARY KEY,
    MaTaiKhoan INT NOT NULL FOREIGN KEY REFERENCES TAI_KHOAN(MaTaiKhoan),
    SoTien FLOAT NOT NULL,
    NgayThanhToan DATETIME DEFAULT GETDATE(),
    PhuongThuc NVARCHAR(50) DEFAULT N'Tiền mặt',
    GhiChu NVARCHAR(255) NULL
);

-- CHÈN DỮ LIỆU MẪU (MOCK DATA)
-- Thêm tài khoản
INSERT INTO TAI_KHOAN (HoTen, SoDienThoai, MatKhau, VaiTro) VALUES 
(N'Quản trị viên', 'admin', '123', 'admin'),
(N'Nguyễn Văn Khách', '00000001', '123', 'client');

-- Thêm xe
INSERT INTO XE (BienSo, LoaiXe, SoGhe) VALUES ('29B-12345', N'Limousine VIP', 7);

-- Thêm chuyến xe
INSERT INTO CHUYEN_XE (MaXe, DiemDi, DiemDen, ThoiGianKhoiHanh, GiaVe) VALUES 
(1, N'Hà Nội', N'Nghệ An', DATEADD(day, 1, GETDATE()), 350000),
(1, N'Hà Nội', N'Thanh Hóa', DATEADD(day, 1, GETDATE()), 300000);

-- Tạo sẵn các ghế trống (Vé trống) cho Chuyến 1 (7 chỗ)
INSERT INTO VE_XE (MaChuyen, MaGhe, GiaVe, TrangThai) VALUES
(1, 'A1', 350000, N'Trống'), (1, 'A2', 350000, N'Trống'), (1, 'A3', 350000, N'Trống'),
(1, 'B1', 350000, N'Trống'), (1, 'B2', 350000, N'Trống'), (1, 'B3', 350000, N'Trống'), (1, 'B4', 350000, N'Trống');

-- Tạo sẵn các ghế trống (Vé trống) cho Chuyến 2 (7 chỗ)
INSERT INTO VE_XE (MaChuyen, MaGhe, GiaVe, TrangThai) VALUES
(2, 'A1', 300000, N'Trống'), (2, 'A2', 300000, N'Trống'), (2, 'A3', 300000, N'Trống'),
(2, 'B1', 300000, N'Trống'), (2, 'B2', 300000, N'Trống'), (2, 'B3', 300000, N'Trống'), (2, 'B4', 300000, N'Trống');

-- Đặt thử 1 ghế A1 ở Chuyến 1 cho ông Khách (TaiKhoan=2)
UPDATE VE_XE SET TrangThai = N'Đã đặt', MaTaiKhoan = 2, NgayDat = GETDATE() WHERE MaChuyen = 1 AND MaGhe = 'A1';
