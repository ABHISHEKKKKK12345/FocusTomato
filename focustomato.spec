# focustomato.spec
# PyInstaller packaging configuration for FocusTomato v1.0.0
# Usage: pyinstaller focustomato.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        # PyQt6 optional modules
        'PyQt6.QtMultimedia',
        'PyQt6.QtSvg',
        'PyQt6.QtPrintSupport',
        # Core package
        'core.app_controller',
        'core.logger',
        'core.models',
        'core.notification_manager',
        'core.settings_manager',
        'core.sound_manager',
        'core.stats_manager',
        'core.storage',
        'core.task_manager',
        'core.timer_engine',
        # UI package
        'ui.dashboard_widget',
        'ui.main_window',
        'ui.settings_dialog',
        'ui.task_panel',
        'ui.theme',
        'ui.timer_widget',
        'ui.widgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy',
        'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FocusTomato',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window on Windows / macOS
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Uncomment and provide icons for distribution:
    # icon='assets/icon.ico',    # Windows
    # icon='assets/icon.icns',   # macOS
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FocusTomato',
)

# macOS .app bundle — comment out if not targeting macOS
app = BUNDLE(
    coll,
    name='FocusTomato.app',
    # icon='assets/icon.icns',
    bundle_identifier='app.focustomato',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'LSUIElement': False,
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
