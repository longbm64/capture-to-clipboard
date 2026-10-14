# CHỤP MÀN HÌNH (Capture to Clipboard)

Ứng dụng chụp vùng màn hình sắc nét chất lượng cao (HD) và ghi chú trực tiếp, hỗ trợ đa nền tảng (**Windows**, **macOS**, **Linux**).

---

## 1. Tính năng nổi bật

- **Chụp nhanh vào Clipboard (`Ctrl + 1` hoặc `PrtSc`)**: Quét chọn vùng màn hình bất kỳ và tự động lưu ảnh chất lượng cao vào bộ nhớ tạm để dán ngay (`Ctrl + V` / `Cmd + V`) vào Zalo, Messenger, Word, Email, v.v.
- **Chụp & Ghi chú (`Ctrl + 2`)**: Quét chọn vùng màn hình và mở bảng công cụ vẽ mũi tên, khung chữ nhật, bút vẽ tự do, chèn chữ (**Roboto**), hoàn tác/xóa tất cả, lưu thành file `.PNG` hoặc copy thẳng vào Clipboard.
- **Khởi động cùng máy tính**: Tùy chọn bật/tắt tự động khởi chạy thu gọn trên khay hệ thống (System Tray / Menu Bar).
- **Đa màn hình & High-DPI / Retina**: Hỗ trợ chuẩn tỷ lệ điểm ảnh thực 1:1 trên màn hình 2K/4K và Apple Retina.

---

## 2. Bảng phím tắt & Thao tác

| Phím tắt | Chức năng | Mô tả thao tác |
| :--- | :--- | :--- |
| **`Ctrl + 1`** / **`PrtSc`** | Chụp nhanh vào Clipboard | Kéo chọn vùng màn hình $\rightarrow$ tự động lưu ảnh vào bộ nhớ tạm để dán ngay (`Ctrl + V`). |
| **`Ctrl + 2`** | Chụp & Mở bảng ghi chú | Kéo chọn vùng màn hình $\rightarrow$ mở cửa sổ vẽ mũi tên, khung vuông, viết chữ rồi Copy hoặc Lưu file. |
| **`Ctrl + C`** / **`Enter`** | Copy ảnh (trong bảng vẽ) | Copy ngay bức ảnh đã vẽ ghi chú vào Clipboard và đóng cửa sổ chỉnh sửa. |
| **`Ctrl + S`** | Lưu thành file ảnh PNG | Xuất bức ảnh đã ghi chú ra file `.PNG` độ phân giải cao. |
| **`Ctrl + Z`** | Hoàn tác (Undo) | Quay lại bước vẽ hoặc ghi chú vừa thực hiện trước đó. |
| **`ESC`** / **Chuột phải** | Hủy thao tác | Thoát nhanh màn hình chọn vùng chụp hoặc đóng cửa sổ ghi chú. |

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

### A. Build trên Windows (`dist/ChupManHinh.exe`)

**Cách 1 — Chạy script tự động (Khuyên dùng):**
Nhấp đúp vào file `build_windows.bat` hoặc chạy trong Terminal:
```powershell
.\build_windows.bat
```

**Cách 2 — Chạy lệnh PyInstaller thủ công:**
```powershell
python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"
python -m PyInstaller --noconfirm --clean --noconsole --onefile --name "ChupManHinh" --icon "assets/logo.ico" --add-data "assets;assets" --hidden-import "pystray._win32" --hidden-import "pynput.keyboard._win32" --hidden-import "pynput.mouse._win32" main.py
```
- **Kết quả sau khi build:** `dist\ChupManHinh.exe` (file `.exe` độc lập duy nhất, nhúng sẵn icon và bộ font Roboto).

---

### B. Build trên macOS (`dist/ChupManHinh.app` & `dist/ChupManHinh-macOS.dmg`)

Script `build_macos.sh` đã được cấu hình để:
1. Tự động kiểm tra và cài đặt `python-tk` qua Homebrew nếu máy chưa có `tkinter`.
2. Tự động khởi tạo môi trường ảo `.venv` để tránh lỗi **PEP 668 (`externally-managed-environment`)** trên macOS / Homebrew.
3. Đóng gói `ChupManHinh.app` chuẩn Retina (`assets/logo.icns`), ký số ad-hoc (`codesign`) cho chip Apple Silicon (M1/M2/M3/M4) và đóng gói bộ cài `.dmg`.

**Các bước thực hiện trên Terminal của macOS:**
```bash
git clone git@github.com:longbm64/capture-to-clipboard.git
cd capture-to-clipboard
chmod +x build_macos.sh
./build_macos.sh
```
*(Nếu đã clone trước đó, chỉ cần chạy: `git pull origin main && ./build_macos.sh`)*

- **Kết quả sau khi build:**
  - `dist/ChupManHinh.app`: Ứng dụng macOS (có thể kéo vào `/Applications`).
  - `dist/ChupManHinh-macOS.dmg`: Bộ cài đặt DMG có sẵn biểu tượng kéo-thả vào `/Applications`.
  - `dist/ChupManHinh-macOS-App.zip`: Bản nén `.zip` của `ChupManHinh.app`.

> **Lưu ý cấp quyền trên macOS lần đầu chạy:**
> Vào **System Settings (Cài đặt hệ thống) $\rightarrow$ Privacy & Security (Quyền riêng tư & Bảo mật)**:
> - **Screen & System Audio Recording (Ghi màn hình):** Bật cho `CHỤP MÀN HÌNH` để cho phép chụp vùng màn hình.
> - **Accessibility (Trợ năng):** Bật cho `CHỤP MÀN HÌNH` để nhận phím tắt toàn cục `Ctrl + 1`, `Ctrl + 2`, `PrtSc`.

---

### C. Build trên Linux (`dist/ChupManHinh`)

```bash
chmod +x build_unix.sh
./build_unix.sh
```
- **Kết quả sau khi build:** `dist/ChupManHinh`.

---

### D. Build tự động trên Cloud (GitHub Actions)

Dự án đã tích hợp sẵn workflow `.github/workflows/build-macos-windows.yml`:
1. Mỗi khi push code lên nhánh `main` (hoặc bấm **Run workflow** trong tab **Actions** trên GitHub), hệ thống sẽ tự động biên dịch song song trên cả máy chủ `macos-latest` và `windows-latest`.
2. Sau khi chạy xong, vào chi tiết lượt chạy trong tab **Actions** để tải về:
   - **`ChupManHinh-macOS-Installer`** (gồm `ChupManHinh-macOS.dmg` và `ChupManHinh-macOS-App.zip`).
   - **`ChupManHinh-Windows-Portable`** (gồm `ChupManHinh.exe`).
