# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Stock Manager Pro
# Build: pyinstaller StockManagerPro.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['files/main.py'],
    pathex=['files'],
    binaries=collect_dynamic_libs('PyQt6'),
    datas=[
        ('files/img/icon_logo.ico', 'img'),
        ('files/img/logo.png',      'img'),
    ],
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.QtSql',
        'sqlite3', '_sqlite3',
        'colors', 'database', 'dialogs', 'main_window', 'theme', 'i18n',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL'],
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
    name='StockManagerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='files/img/icon_logo.ico',         # taskbar + exe icon
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StockManagerPro',
)
