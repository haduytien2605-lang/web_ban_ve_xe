// --- LOGIC CHO KHÁCH HÀNG ---
function selectSeat(seatElement) {
    seatElement.classList.toggle('selected');
    updateTotalPrice();
}

function updateTotalPrice() {
    const selectedSeats = document.querySelectorAll('.seat.selected');
    const pricePerSeat = 300000;
    const total = selectedSeats.length * pricePerSeat;
    
    const display = document.getElementById('total-price');
    if (display) {
        display.innerText = total.toLocaleString('vi-VN') + 'đ';
    }
}

// --- LOGIC CHO CHỦ XE (ADMIN) ---
function confirmTicket(ticketId) {
    // Giả lập gửi yêu cầu xác nhận về server
    if(confirm("Bạn có chắc chắn muốn xác nhận vé này đã thanh toán?")) {
        console.log("Đã xác nhận vé ID:", ticketId);
        alert("Cập nhật trạng thái thành công!");
        location.reload(); // Load lại trang để cập nhật danh sách
    }
}

// Hàm lưu địa điểm (đã có từ source 3)
function handleSearch() {
    const departure = document.getElementById('departure').value;
    const destination = document.getElementById('destination').value;
    
    localStorage.setItem('diem_di', departure);
    localStorage.setItem('diem_den', destination);
    location.href = '/pick-time';
}