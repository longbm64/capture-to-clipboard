# Quy tắc Ghi nhận & Quản lý Phiên bản (Versioning Policy)

Quy tắc này luôn được kích hoạt (`trigger: always_on`). Bất cứ khi nào Agent hoặc lập trình viên thực hiện chỉnh sửa mã nguồn, bổ sung tính năng, vá lỗi hoặc chuẩn bị commit/push code:

## 1. Hành vi bắt buộc trước khi kết thúc tác vụ hoặc push code:
1. **Tăng số phiên bản trong `app/__init__.py`:**
   - Cập nhật biến `__version__ = "X.Y.Z"` và `APP_VERSION = __version__` theo chuẩn Semantic Versioning:
     - `PATCH` (Z): Vá lỗi, cải tiến nhỏ, chỉnh sửa giao diện / màu sắc / độ nét.
     - `MINOR` (Y): Bổ sung tính năng mới tương thích ngược (ví dụ thêm công cụ vẽ, thêm ngôn ngữ).
     - `MAJOR` (X): Thay đổi kiến trúc lớn hoặc thay đổi đột phá.
2. **Cập nhật `CHANGELOG.md`:**
   - Ghi lại số phiên bản mới, ngày phát hành, và tóm tắt ngắn gọn các điểm mới/sửa đổi.
3. **Hiển thị phiên bản & Tác quyền KAHUB PLATFORM đồng bộ:**
   - Cửa sổ ứng dụng (Cài đặt & Hướng dẫn, Editor): Phải hiển thị phiên bản ở thanh tiêu đề (`f"{APP_NAME} v{APP_VERSION}"`).
   - Bảng hướng dẫn & cài đặt: Phải hiển thị phiên bản ở badge header và footer.
   - Bắt buộc hiển thị thông tin tác quyền **`⚡ Được phát triển bởi KAHUB PLATFORM`** (hoặc tiếng Anh *Developed by KAHUB PLATFORM*).
   - PyInstaller spec (`ChupManHinh_macOS.spec`): Phải nạp trực tiếp `APP_VERSION` từ `app` để đồng bộ vào `Info.plist` của file `.app`.
