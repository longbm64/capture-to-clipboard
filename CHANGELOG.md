# Nhật Ký Phiên Bản (Changelog)

Toàn bộ các phiên bản phát hành của **Capture To Clipboard** được ghi nhận và tuân thủ theo chuẩn [Semantic Versioning (SemVer)](https://semver.org/).

---

## [v1.3.7] - 2026-10-20

### 🎯 Đường gióng tâm tọa độ toàn màn hình & Tối ưu 0ms phản hồi
- **Thước ngắm chữ thập X, Y (Full-screen Crosshair Guidelines):**
  - Tự động thay thế con trỏ mặc định bằng hai đường gióng trục ngang & trục dọc toàn màn hình với màu chủ đạo rõ nét.
  - Hiển thị nhãn tọa độ `(X, Y)` dạng pill nền tối Slate-900, viền màu chủ đạo và chữ trắng tương phản cao ngay cạnh con trỏ chuột.
  - Tối ưu hóa phản hồi tức thì `0ms` đồng bộ trên sự kiện chuột, đạt độ mượt tối đa theo tần số quét màn hình (60Hz - 120Hz ProMotion).
- **Khắc phục lỗi khởi động treo ngầm trên macOS:**
  - Bổ sung cấu hình `ApplePersistenceIgnoreState = YES` trước khi nạp Tkinter, ngăn chặn hoàn toàn việc macOS hiển thị modal cảnh báo khôi phục crash ngầm gây đóng băng tiến trình.
- **Trích xuất ảnh Lossless 1:1 siêu nét:**
  - Áp dụng kỹ thuật đọc dữ liệu raw bitmap CGImage trực tiếp trên macOS, loại bỏ nén trung gian và phát hiện hệ số Retina chính xác theo màn hình hiển thị.

---

## [v1.3.6] - 2026-10-20

### 🛡️ Khắc phục xung đột phím tắt trình duyệt trên macOS
- **Chuyển phím tắt chụp màn hình trên macOS sang `Ctrl + 1` và `Ctrl + 2`:**
  - Giải phóng hoàn toàn tổ hợp `Cmd + 1` và `Cmd + 2` trên macOS, chấm dứt triệt để tình trạng chặn thao tác chuyển tab số 1 và số 2 trong các trình duyệt (Chrome, Safari, Brave, Arc, Edge...).
  - Đồng nhất 100% phím tắt chụp ảnh trên toàn bộ hệ điều hành (macOS, Windows, Linux) với `Ctrl + 1` (Chụp nhanh) và `Ctrl + 2` (Chụp & Ghi chú).
  - Tối ưu bộ bắt sự kiện cấp thấp Quartz Event Intercept: chỉ can thiệp phím Control (`^`), hoàn trả toàn bộ sự kiện Command (`⌘`) cho hệ thống và ứng dụng tiền cảnh với độ trễ 0ms.
  - Đồng bộ cập nhật bảng tra cứu phím tắt trong giao diện Cài đặt, thông báo Toast, Menu khay hệ thống (Menu Bar / Tray) và tài liệu hướng dẫn.

---

## [v1.3.5] - 2026-10-20

### ⌨️ Tối ưu phím tắt Sao chép trong Trình chỉnh sửa ảnh (Annotation Editor)
- **Chuyển phím tắt sao chép từ `Enter` sang `Cmd + C` (hoặc `Ctrl + C` trên Windows/Linux):**
  - Cập nhật nhãn nút bấm thành `Sao chép (Cmd+C)` (trên macOS) / `Sao chép (Ctrl+C)` (trên Windows) và `Copy (Cmd+C)` / `Copy (Ctrl+C)` trong chế độ tiếng Anh.
  - Phím `Cmd + C` (và `Ctrl + C`) kích hoạt sao chép ảnh nét cao vào bộ nhớ tạm (Clipboard) và đóng cửa sổ chỉnh sửa.
  - Phím `Enter` / `Return` không còn tự động sao chép và đóng cửa sổ khi đang vẽ, tránh tình trạng thao tác nhầm; phím `Enter` chỉ dùng để xác nhận lưu nội dung khi đang gõ chữ (`Text Annotation`).
  - Đồng bộ cập nhật thanh trạng thái dưới chân bảng vẽ và bảng hướng dẫn phím tắt trong Cài đặt & file README.

---

## [v1.3.4] - 2026-10-20

### ⚡ Tối ưu hiệu năng kéo chọn vùng (Zero-Latency Dragging)
- **Loại bỏ hoàn toàn độ trễ (delay/lag) khi quét chọn vùng chụp:**
  - Áp dụng cơ chế phân tách xử lý hình học vector thời gian thực (`0ms` độ trễ, bám chuột `120 FPS` chuẩn ProMotion màn hình macOS).
  - Tối ưu hóa điều tiết làm mới mảng ảnh sáng bên trong vùng chọn theo nhịp đồ họa mượt mà (frame pacing), loại bỏ hiện tượng tắc nghẽn hàng đợi sự kiện chuột do liên tục cắt và nạp bitmap raster.
  - Loại bỏ các lệnh truy vấn `canvas.bbox()` đồng bộ trên từng pixel chuột, chuyển sang tính toán tọa độ vector trực tiếp cực nhanh.

---

## [v1.3.3] - 2026-10-20

### 🚀 Quản lý hiển thị Dock Icon trên macOS
- **Ẩn hoàn toàn icon ở Dock khi thu gọn về System Tray:**
  - Khi bấm nút `X` (đóng cửa sổ), `-` (thu nhỏ), phím `ESC` hoặc `Cmd + W`, ứng dụng sẽ tự động thu xuống Menu Bar / System Tray mà **không tắt hẳn**, đồng thời **tự động đóng/ẩn icon ở thanh Dock của macOS** (chuyển sang `NSApplicationActivationPolicyAccessory`).
  - Khi mở lại cửa sổ Cài đặt & Hướng dẫn (từ khay hệ thống) hoặc mở Trình chỉnh sửa ảnh (`Cmd + 2`), icon trên thanh Dock sẽ tự động hiển thị lại và đưa cửa sổ lên tiền cảnh (`NSApplicationActivationPolicyRegular`).
  - Hỗ trợ đóng nhanh cửa sổ bằng phím tắt chuẩn macOS `Cmd + W` (hoặc `Ctrl + W` trên Windows).

---

## [v1.3.2] - 2026-10-20

### 🎨 Tinh gọn Cửa sổ Cài đặt & Hướng dẫn
- **Xóa Header Card trên cùng:** Gỡ bỏ hoàn toàn khung header giới thiệu ở đầu bảng cài đặt, giúp cửa sổ mở lên trực quan, gọn nhẹ và bắt đầu ngay vào các tùy chọn cấu hình.
- **Dời Logo xuống Footer:** Chuyển logo thương hiệu ứng dụng xuống thanh footer bên cạnh tên ứng dụng và số phiên bản (`Capture To Clipboard v1.3.2`).
- **Liên kết KAHUB PLATFORM:** Nút badge "⚡ Được phát triển bởi KAHUB PLATFORM ↗" hỗ trợ click chuột để mở trực tiếp trang chủ **`https://kahub.vn`** trên trình duyệt mặc định với hiệu ứng hover và con trỏ tay (hand cursor).

---

## [v1.3.1] - 2026-10-20

### 🧹 Tối giản giao diện chụp màn hình
- **Gỡ bỏ thanh ghi chú ở đỉnh màn hình (Top Banner Note):**
  - Xóa hoàn toàn thanh note hướng dẫn ở cạnh trên màn hình khi quét chọn vùng chụp (`overlay`), giữ màn hình luôn sạch sẽ, thoáng đãng và không bị che khuất bất kỳ chi tiết nào của ứng dụng bên dưới.
  - Vẫn giữ nguyên thao tác tiện lợi: Phím `ESC` hoặc click chuột phải để hủy chụp, click đúp hoặc phím `Space`/`Enter` để chụp toàn màn hình.

---

## [v1.3.0] - 2026-10-20

### 🚀 Tính năng & Giao diện mới
- **Quản lý & Hiển thị Phiên bản đồng bộ:**
  - Hiển thị phiên bản `v1.3.0` trực tiếp trên thanh tiêu đề của toàn bộ cửa sổ ứng dụng (Cửa sổ Cài đặt & Hướng dẫn, Cửa sổ Chỉnh sửa Ghi chú).
  - Hiển thị badge phiên bản `v1.3.0 • Retina HD` trong Card thông tin thương hiệu.
  - Tự động đồng bộ số phiên bản `__version__` vào `Info.plist` của gói ứng dụng macOS (`CFBundleShortVersionString`, `CFBundleVersion`).
- **Tác quyền KAHUB PLATFORM:**
  - Bổ sung thanh thông tin bản quyền ở chân bảng hướng dẫn: **`⚡ Được phát triển bởi KAHUB PLATFORM`** (hỗ trợ chuyển đổi song ngữ: *Developed by KAHUB PLATFORM*).
- **Giao diện Vector Native sắc nét 100% trên màn hình Retina (macOS High-DPI):**
  - Chuyển đổi toàn bộ nút bấm (`ModernPillButton`), bộ chọn kích thước (`SizeDotButton`), bảng chọn màu (`ColorSwatchButton`) và hộp kiểm (`ModernCheckbox`) từ ảnh raster bitmap sang vector `tk.Canvas` thuần.
  - Text được kết xuất trực tiếp bằng Apple CoreText cho độ sắc nét tối đa, viền nút bo góc mượt mà qua Quartz 2D, loại bỏ triệt để hiện tượng mờ nhòe do phóng đại bitmap 1x.
- **Nhận diện thương hiệu mới:**
  - Cập nhật logo mới máy ảnh quét clipboard vào `assets/logo.png`, `assets/logo.icns`, `assets/logo.ico`.
  - Tích hợp logo thương hiệu mini vào tiêu đề bảng phím tắt & hướng dẫn.
- **Trải nghiệm người dùng:**
  - Loại bỏ các toast thông báo phụ gây xao nhãng, chỉ hiển thị thông báo toast khi quét vùng ảnh hoàn tất.
  - Bổ sung lớp màng mỏng bán trong suốt (dimmed overlay) giúp người dùng nhận diện ngay tức thì khi hệ thống vào chế độ chụp màn hình.

---

## [v1.2.0] - 2026-10-18

### 🌟 Cải tiến
- Đổi tên ứng dụng chính thức thành **Capture To Clipboard**.
- Bổ sung bộ chuyển đổi ngôn ngữ **Tiếng Việt** & **English** tức thì, tự động lưu vào `settings.json`.
- Tự động thu nhỏ xuống khay hệ thống (System Tray) khi bấm nút `X` hoặc `-`.
- Hỗ trợ phím cứng `PrtSc` để chụp nhanh (tương đương `Cmd + 1` / `Ctrl + 1`).
- Tối ưu cơ chế chụp ảnh gốc độ phân giải thực 1:1, không nén hay suy hao chất lượng.

---

## [v1.1.0] - 2026-10-14

### 🎨 Bộ công cụ chỉnh sửa ảnh
- Thanh công cụ vẽ & ghi chú: Bút vẽ, bút dạ quang, mũi tên định hướng, khung chữ nhật, elip, đường thẳng, chèn text đa ngôn ngữ (font Roboto), làm mờ vùng nhạy cảm (blur).
- Quản lý lịch sử thao tác: Hoàn tác (`Cmd + Z`), Làm lại, Xóa toàn bộ.
- Lưu ảnh chất lượng cao ra file (`Cmd + S`) hoặc sao chép thẳng vào Clipboard (`Enter` / `Cmd + C`).

---

## [v1.0.0] - 2026-10-10

### 🚀 Khởi tạo dự án
- Bắt phím tắt toàn cục chụp vùng màn hình trên macOS (`Cmd + 1`, `Cmd + 2`) và Windows (`Ctrl + 1`, `Ctrl + 2`).
- Sao chép trực tiếp dữ liệu hình ảnh vào bộ nhớ tạm hệ thống (System Clipboard).
- Biểu tượng điều khiển trên khay hệ thống (System Tray / Menu Bar).
