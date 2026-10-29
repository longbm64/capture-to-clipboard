# Capture To Clipboard (Native C++ Edition)

Ứng dụng chụp vùng màn hình sắc nét chất lượng cao (HD 1:1 Lossless) và ghi chú trực tiếp, được viết bằng **Native C++17 (Win32 API & GDI+ Double-Buffering)** tối ưu hiệu năng cao, siêu nhẹ (~1.5 MB `.exe` độc lập duy nhất, khởi động tức thì `< 10ms`, dựng hình `120–240+ FPS` không giật lag), hỗ trợ **song ngữ Tiếng Việt / Tiếng Anh** (mặc định Tiếng Việt, tự động ghi nhớ ngôn ngữ đã chọn).

> **Lưu ý:** Toàn bộ mã nguồn Python/Tkinter cũ đã được lưu trữ đầy đủ trong thư mục [`old-code/`](old-code/).

---

## 1. Ưu điểm của phiên bản C++ Native

- **Tốc độ phản hồi tức thì (`Zero-Latency`)**: Chụp toàn bộ màn hình đa màn hình (`Virtual Desktop`) qua `BitBlt` và làm tối nền bằng toán học nguyên 32-bit chỉ trong **~2–4 ms**.
- **Mượt mà 120–240+ FPS (`Hardware Double-Buffering`)**: Màn hình quét chọn vùng (`RegionSelectorOverlay`) và trình chỉnh sửa ghi chú (`AnnotationEditor`) đều vẽ trên Backbuffer DC, loại bỏ hoàn toàn hiện tượng nhấp nháy hay trễ khung hình khi kéo chuột.
- **Độc lập 100% (`Single Portable EXE`)**: Nhúng trực tiếp bộ icon đa độ phân giải (`assets/logo.ico`) và bộ font chữ **Roboto** (`Roboto-Regular.ttf`, `Roboto-Bold.ttf`) vào tài nguyên `.rc` của file `.exe` với liên kết tĩnh (`/MT /O2 /GL /LTCG`) — không cần cài Python hay thư viện phụ thuộc.
- **Đầy đủ tính năng**:
  - **Chụp nhanh vào Clipboard (`Ctrl + 1` hoặc `PrtSc`)**: Quét chọn vùng màn hình bất kỳ và tự động lưu ảnh chất lượng gốc 1:1 (`PNG` + `image/png` + `CF_DIB` chuẩn DPI) vào bộ nhớ tạm để dán ngay (`Ctrl + V`) vào Zalo, Messenger, Slack, Word, Email...
  - **Chụp & Ghi chú (`Ctrl + 2`)**: Quét chọn vùng màn hình và mở bảng công cụ vẽ **Mũi tên**, **Bút vẽ**, **Bút dạ quang**, **Khung chữ nhật**, **Elip**, **Đường thẳng**, **Chèn chữ (Roboto)**, **Làm mờ (Pixelate)**, **Hoàn tác / Làm lại / Xóa hết**, kéo di chuyển hoặc chỉnh lại kích thước các nét đã vẽ, lưu thành file `.PNG` / `.JPG` / `.BMP` hoặc copy thẳng vào Clipboard.
  - **Song ngữ Tiếng Việt & Tiếng Anh**: Chuyển đổi tức thì ngay trong cửa sổ cài đặt, tự động lưu vào `settings.json`.
  - **Tự động thu xuống System Tray khi bấm `X`, `-` hoặc `ESC`**: Giữ màn hình làm việc gọn gàng, luôn sẵn sàng nhận phím tắt.
  - **Khởi động cùng máy tính**: Tùy chọn bật/tắt tự động khởi chạy thu gọn trên khay hệ thống (System Tray).

---

## 2. Cấu trúc thư mục dự án

```text
capture-to-clipboard/
├── src/                      # Mã nguồn C++17 Native
│   ├── main.cpp              # Điểm vào ứng dụng, Single-Instance Mutex & Coordinator
│   ├── common.h              # Tiện ích chung, DPI scaling, màu sắc & GDI+ helpers
│   ├── i18n.h / i18n.cpp     # Đa ngôn ngữ (Tiếng Việt / Tiếng Anh) & đọc/ghi settings.json
│   ├── autostart.h / .cpp    # Quản lý khởi động cùng Windows (Registry Run & StartupApproved)
│   ├── platform_utils.h/.cpp # Chụp màn hình GDI BitBlt, Clipboard Lossless PNG/CF_DIB, Font & Icon
│   ├── hotkeys.h / .cpp      # Phím tắt toàn cục (RegisterHotKey + WH_KEYBOARD_LL hook cho PrtSc)
│   ├── tray.h / .cpp         # Quản lý System Tray & Menu ngữ cảnh
│   ├── toast.h / .cpp        # Thông báo nổi (Toast Notification) góc dưới phải màn hình
│   ├── overlay.h / .cpp      # Màn hình kéo chọn vùng chụp 240+ FPS Double-Buffered
│   ├── editor.h / .cpp       # Trình vẽ & ghi chú Vector tương tác (Ctrl + 2)
│   ├── settings_window.h/.cpp# Cửa sổ Cài đặt & Bảng hướng dẫn phím tắt (Soft Daylight Theme)
│   └── resource.h / app.rc   # Tài nguyên Win32 nhúng Icon & Font Roboto vào .exe
├── assets/                   # Tài nguyên gốc (logo.ico, fonts/Roboto-*.ttf, settings.json)
├── dist/                     # Chứa file thực thi độc lập CaptureToClipboard.exe sau khi build
├── old-code/                 # Toàn bộ mã nguồn Python/Tkinter cũ được lưu trữ lại
├── CMakeLists.txt            # Cấu hình CMake cho dự án C++17
├── build_windows.bat         # Script biên dịch tự động ra dist\CaptureToClipboard.exe
└── run_windows.bat           # Script biên dịch (nếu chưa có) và chạy ngay ứng dụng
```

---

## 3. Bảng phím tắt & Thao tác

| Phím tắt | Chức năng | Mô tả thao tác |
| :--- | :--- | :--- |
| **`Ctrl + 1`** / **`PrtSc`** | Chụp & Sao chép ngay | Kéo chọn vùng màn hình $\rightarrow$ tự động lưu ảnh vào bộ nhớ tạm để dán ngay (`Ctrl + V`). |
| **`Ctrl + 2`** | Chụp & Ghi chú trên ảnh | Kéo chọn vùng màn hình $\rightarrow$ mở cửa sổ vẽ mũi tên, khung vuông, viết chữ rồi Copy hoặc Lưu file. |
| **`Kéo giữ chuột`** | Di chuyển / Chỉnh nét vẽ | Nhấn giữ vào mũi tên, chữ hoặc khung đã vẽ để dời vị trí hoặc kéo các nút tròn để chỉnh lại hướng/kích thước. |
| **`Nhấp đúp chuột`** | Sửa nội dung chữ | Nhấp đúp chuột trái vào chữ đã thêm trên ảnh để chỉnh sửa lại nội dung. |
| **`Enter`** / **`Ctrl + C`** | Hoàn tất & Sao chép | Copy ngay bức ảnh đã vẽ ghi chú vào Clipboard và đóng cửa sổ chỉnh sửa. |
| **`Ctrl + S`** | Lưu thành file ảnh | Xuất bức ảnh đã ghi chú ra file `.PNG`, `.JPG` hoặc `.BMP` độ phân giải cao. |
| **`Ctrl + Z`** / **`Delete`** | Hoàn tác / Xóa nét vẽ | Quay lại bước trước đó hoặc xóa nét đang chọn. |
| **`ESC`** / **Chuột phải** | Hủy thao tác | Thoát nhanh màn hình chọn vùng chụp hoặc thu gọn cửa sổ xuống khay hệ thống. |

---

## 4. Hướng dẫn Build & Chạy ứng dụng (C++)

### A. Build nhanh bằng Script (`build_windows.bat`)
Nhấp đúp vào `build_windows.bat` hoặc chạy trên Terminal (PowerShell / CMD):
```powershell
.\build_windows.bat
```
- Kết quả: File thực thi độc lập duy nhất tại `dist\CaptureToClipboard.exe`.

### B. Build bằng CMake
```powershell
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

### C. Chạy kiểm tra tự động (`--self-test`)
```powershell
.\dist\CaptureToClipboard.exe --self-test
```

### D. Ký số Authenticode & Cài đặt chứng chỉ tin cậy (`Root Trust`)
Ứng dụng được tích hợp sẵn cơ chế tự động ký số Authenticode kèm dấu thời gian RFC 3161 (DigiCert Timestamp) và làm sạch bộ nhớ đệm Smart App Control:
- **Tự động ký khi build**: Cả `build_windows.bat` và `CMake` đều tự động kích hoạt script `sign_and_trust.ps1` sau khi biên dịch xong.
- **Cài đặt chứng chỉ vào hệ thống để đạt trạng thái `Valid`**:
  Nhấp đúp hoặc chuột phải chọn **Run as administrator** file:
  ```powershell
  .\trust_cert_admin.bat
  ```
  hoặc chạy trong PowerShell (Run as Administrator):
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\sign_and_trust.ps1
  ```
- **Kiểm tra trạng thái chữ ký số**:
  ```powershell
  Get-AuthenticodeSignature .\dist\CaptureToClipboard.exe
  ```
  Kết quả hiển thị `Status: Valid` (Chữ ký hợp lệ, chứng chỉ số được hệ thống Windows và Smart App Control tin cậy hoàn toàn).

