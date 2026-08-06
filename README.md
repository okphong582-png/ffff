# 📱 iOS Box Phone PC Screen Mirroring & Touch Control (Python)

Ứng dụng Python dành cho **Box Phone / Phone Farm / Điều khiển iPhone cá nhân trên PC Windows** qua cáp kết nối USB Lightning.
Khi cắm cáp Lightning vào máy tính PC, ứng dụng tự động phát hiện thiết bị (Plug-and-Play), nhận luồng màn hình trực tiếp độ trễ thấp và cho phép nhấn chuột / vuốt / gõ bàn phím từ PC để điều khiển iPhone.

---

## 🌟 Tính năng nổi bật

- **Tự động nhận diện cáp USB Lightning**: Tự động phát hiện khi cắm hoặc rút cáp iPhone mà không cần thao tác kết nối lại thủ công.
- **Truyền màn hình độ nét cao (Live Stream)**: Nhận luồng MJPEG tốc độ cao từ WebDriverAgent với số khung hình/giây (FPS) thực tế.
- **Điều khiển màn hình cảm ứng từ PC (Touch Bridge)**:
  - **Click chuột**: Tự chuyển thành thao tác chạm điểm (Tap) trên màn hình iPhone.
  - **Giữ và kéo chuột**: Tự chuyển thành thao tác vuốt màn hình (Swipe / Scroll).
  - **Bàn phím PC**: Gõ chữ trực tiếp từ PC vào các ô nhập dữ liệu trên iPhone.
  - **Thanh phím điều khiển cứng**: Phím Home, Chuyển ứng dụng (App Switcher), Khóa/Mở nguồn màn hình (Power), Tăng/Giảm âm lượng.
- **Hỗ trợ Box Phone Farm (Nhiều máy)**: Quản lý và điều khiển đồng thời nhiều iPhone kết nối qua nhiều cổng USB trên PC với giao diện dạng lưới (Grid View).

---

## 🛠️ Hướng dẫn Cài đặt & Chuẩn bị

### 1. Cài đặt Python Dependencies
Mở Terminal hoặc Command Prompt tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### 2. Cài đặt iTunes Driver trên PC (Windows)
Để PC nhận diện cáp USB Lightning và giao tiếp với service `usbmuxd` của Apple, máy tính cần cài đặt **iTunes 64-bit** (bản chính thức từ Apple hoặc Microsoft Store).

### 3. Chuẩn bị trên iPhone (Một lần duy nhất)
1. **Bật Developer Mode**:
   Vào `Cài đặt` -> `Quyền riêng tư & Bảo mật` -> kéo xuống dưới chọn `Chế độ Nhà phát triển (Developer Mode)` -> Bật và Khởi động lại iPhone.
2. **Cài đặt WebDriverAgent (WDA)**:
   - Cài đặt `WebDriverAgentRunner.ipa` lên iPhone bằng các công cụ như **Sideloadly**, **AltStore**, **3uTools**, hoặc **Xcode**.
   - Khởi chạy WebDriverAgent trên iPhone để khởi tạo server điều khiển qua cổng 8100/9100.

---

## 🚀 Chạy ứng dụng

Sau khi cài đặt xong các thư viện, chạy lệnh:
```bash
python main.py
```

### Hướng dẫn sử dụng:
1. Cắm cáp Lightning USB kết nối iPhone với PC.
2. Ứng dụng sẽ tự động phát hiện thiết bị và hiển thị thẻ iPhone lên màn hình.
3. Dùng chuột nhấp hoặc kéo trên hình ảnh màn hình iPhone để thao tác trực tiếp!
