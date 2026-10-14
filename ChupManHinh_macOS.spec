# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Spec File for macOS Application Bundle (ChupManHinh.app)."""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'pystray._darwin',
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'PIL._tkinter_finder',
        'AppKit',
        'Foundation',
        'Quartz',
        'HIServices',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ChupManHinh',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChupManHinh',
)

app = BUNDLE(
    coll,
    name='ChupManHinh.app',
    icon='assets/logo.icns',
    bundle_identifier='com.chupmanhinh.hd.app',
    info_plist={
        'CFBundleName': 'ChupManHinh',
        'CFBundleDisplayName': 'CHỤP MÀN HÌNH',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'NSScreenCaptureUsageDescription': (
            'Ứng dụng CHỤP MÀN HÌNH cần quyền Ghi màn hình (Screen Recording) '
            'để chụp vùng màn hình sắc nét chất lượng cao.'
        ),
        'NSAppleEventsUsageDescription': (
            'Ứng dụng CHỤP MÀN HÌNH cần quyền Trợ năng (Accessibility) '
            'để nhận phím tắt chụp nhanh Ctrl+1, Ctrl+2 và PrtSc.'
        ),
    },
)
