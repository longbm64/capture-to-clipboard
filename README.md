<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="Capture To Clipboard Logo" />
</p>

<h1 align="center">Capture To Clipboard</h1>

<p align="center">
  <b>Ứng dụng chụp vùng màn hình sắc nét chất lượng cao (HD) & Ghi chú trực tiếp vào bộ nhớ tạm</b><br />
  Hỗ trợ macOS, Windows, Linux • Song ngữ Tiếng Việt & Tiếng Anh
</p>

---

## 1. Tính năng nổi bật

- **Chụp nhanh vào Clipboard (`Cmd + 1` trên macOS / `Ctrl + 1` trên Windows & Linux / `PrtSc`)**: Quét chọn vùng màn hình bất kỳ và tự động lưu ảnh chất lượng cao vào bộ nhớ tạm để dán ngay (`Cmd + V` / `Ctrl + V`) vào Zalo, Messenger, Slack, Word, Email, v.v.
- **Chụp & Ghi chú (`Cmd + 2` trên macOS / `Ctrl + 2` trên Windows & Linux)**: Quét chọn vùng màn hình và mở bảng công cụ vẽ mũi tên, khung chữ nhật, bút dạ quang, làm mờ, chèn chữ (**Roboto**), hoàn tác/xóa tất cả, lưu thành file `.PNG` hoặc copy thẳng vào Clipboard.
- **Song ngữ Tiếng Việt & Tiếng Anh**: Chuyển đổi tức thì ngay trong cửa sổ cài đặt, tự động lưu lựa chọn vào `settings.json` cho các lần mở tiếp theo.
- **Tự động thu xuống System Tray khi bấm `X` hoặc `-`**: Giữ màn hình làm việc gọn gàng, luôn sẵn sàng nhận phím tắt.
- **Khởi động cùng máy tính**: Tùy chọn bật/tắt tự động khởi chạy thu gọn trên khay hệ thống (System Tray / Menu Bar).

---

## 2. Bảng phím tắt & Thao tác

| Phím tắt (macOS) | Phím tắt (Windows/Linux) | Chức năng | Mô tả thao tác |
| :--- | :--- | :--- | :--- |
| **`Cmd + 1`** | **`Ctrl + 1`** / **`PrtSc`** | Chụp & Sao chép ngay | Kéo chọn vùng màn hình $\rightarrow$ tự động lưu ảnh vào bộ nhớ tạm để dán ngay (`Cmd + V` / `Ctrl + V`). |
| **`Cmd + 2`** | **`Ctrl + 2`** | Chụp & Ghi chú trên ảnh | Kéo chọn vùng màn hình $\rightarrow$ mở cửa sổ vẽ mũi tên, khung vuông, viết chữ rồi Copy hoặc Lưu file. |
| **`Cmd + C`** | **`Ctrl + C`** | Hoàn tất & Sao chép | Copy ngay bức ảnh đã vẽ ghi chú vào Clipboard và đóng cửa sổ chỉnh sửa. |
| **`Cmd + S`** | **`Ctrl + S`** | Lưu thành file ảnh | Xuất bức ảnh đã ghi chú ra file `.PNG`, `.JPG` hoặc `.WebP` độ phân giải cao. |
| **`Cmd + Z`** / **`Delete`** | **`Ctrl + Z`** / **`Delete`** | Hoàn tác / Xóa nét vẽ | Quay lại bước trước đó hoặc xóa nét đang chọn. |
| **`ESC`** / **Chuột phải** | **`ESC`** / **Chuột phải** | Hủy thao tác | Thoát nhanh màn hình chọn vùng chụp hoặc thu gọn cửa sổ xuống khay hệ thống. |

---

## 3. Chạy trực tiếp từ mã nguồn (Development)

### Windows
Nhấp đúp vào file `run_windows.bat` hoặc chạy trên Terminal (PowerShell / CMD):
```powershell
python -m pip install -r requirements.txt
python main.py
```

### macOS / Linux
```bash
chmod +x run_unix.sh
./run_unix.sh
```

---

## 4. Hướng dẫn Build (Đóng gói ứng dụng độc lập)

### A. Build trên Windows (`dist/CaptureToClipboard.exe`)

**Cách 1 — Chạy script tự động (Khuyên dùng):**
Nhấp đúp vào file `build_windows.bat` hoặc chạy trong Terminal:
```powershell
.\build_windows.bat
```

**Cách 2 — Chạy lệnh PyInstaller thủ công:**
```powershell
python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"
python -m PyInstaller --noconfirm --clean --noconsole --onefile --name "CaptureToClipboard" --icon "assets/logo.ico" --add-data "assets;assets" --hidden-import "pystray._win32" --hidden-import "pynput.keyboard._win32" --hidden-import "pynput.mouse._win32" main.py
```
- **Kết quả sau khi build:** `dist\CaptureToClipboard.exe` (file `.exe` độc lập duy nhất, nhúng sẵn icon và bộ font Roboto).

---

### B. Build trên macOS (`dist/Capture To Clipboard.app` & `dist/CaptureToClipboard-macOS.dmg`)

Script `build_macos.sh` đã được cấu hình để:
1. Tự động kiểm tra và cài đặt `python-tk` qua Homebrew nếu máy chưa có `tkinter`.
2. Tự động khởi tạo môi trường ảo `.venv` để tránh lỗi **PEP 668 (`externally-managed-environment`)** trên macOS / Homebrew.
3. Đóng gói `Capture To Clipboard.app` chuẩn Retina (`assets/logo.icns`), ký số ad-hoc (`codesign`) cho chip Apple Silicon (M1/M2/M3/M4) và đóng gói bộ cài `.dmg`.

**Các bước thực hiện trên Terminal của macOS:**
```bash
git clone git@github.com:longbm64/capture-to-clipboard.git
cd capture-to-clipboard
chmod +x build_macos.sh
./build_macos.sh
```
*(Nếu đã clone trước đó, chỉ cần chạy: `git pull origin main && ./build_macos.sh`)*

- **Kết quả sau khi build:**
  - `dist/Capture To Clipboard.app`: Ứng dụng macOS (có thể kéo vào `/Applications`).
  - `dist/CaptureToClipboard-macOS.dmg`: Bộ cài đặt DMG có sẵn biểu tượng kéo-thả vào `/Applications`.
  - `dist/CaptureToClipboard-macOS-App.zip`: Bản nén `.zip` của `Capture To Clipboard.app`.

> **Lưu ý cấp quyền trên macOS lần đầu chạy:**
> Vào **System Settings (Cài đặt hệ thống) $\rightarrow$ Privacy & Security (Quyền riêng tư & Bảo mật)**:
> - **Screen & System Audio Recording (Ghi màn hình):** Bật cho `Capture To Clipboard` để cho phép chụp vùng màn hình.
> - **Accessibility (Trợ năng):** Bật cho `Capture To Clipboard` để nhận phím tắt toàn cục `Cmd + 1`, `Cmd + 2`.

---

### C. Build trên Linux (`dist/CaptureToClipboard`)

```bash
chmod +x build_unix.sh
./build_unix.sh
```
- **Kết quả sau khi build:** `dist/CaptureToClipboard`.

---

### D. Build tự động trên Cloud (GitHub Actions)

Dự án đã tích hợp sẵn workflow `.github/workflows/build-macos-windows.yml`:
1. Mỗi khi push code lên nhánh `main` (hoặc bấm **Run workflow** trong tab **Actions** trên GitHub), hệ thống sẽ tự động biên dịch song song trên cả máy chủ `macos-latest` và `windows-latest`.
2. Sau khi chạy xong, vào chi tiết lượt chạy trong tab **Actions** để tải về:
   - **`CaptureToClipboard-macOS-Installer`** (gồm `CaptureToClipboard-macOS.dmg` và `CaptureToClipboard-macOS-App.zip`).
   - **`CaptureToClipboard-Windows-Portable`** (gồm `CaptureToClipboard.exe`).

---

## 5. Thông tin Phát triển & Bản quyền

- **Phiên bản hiện tại:** `v1.3.4` (Xem chi tiết tại [CHANGELOG.md](CHANGELOG.md))
- **Đơn vị phát triển:** [**KAHUB PLATFORM** (kahub.vn)](https://kahub.vn)
- **Chính sách phiên bản:** Mọi thay đổi mã nguồn, tính năng, sửa lỗi hoặc push code đều được đánh số phiên bản theo chuẩn SemVer và đồng bộ tự động trên thanh tiêu đề cửa sổ, giao diện và gói phát hành.

