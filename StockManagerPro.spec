# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Stock Manager Pro v2
# Build: cd src && pyinstaller StockManagerPro.spec --noconfirm

from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['files/main.py'],
    pathex=['files'],
    binaries=collect_dynamic_libs('PyQt6'),
    datas=[
        ('files/img/icon_logo.ico', 'img'),
        ('files/img/logo.png',      'img'),
        ('files/img/icons',         'img/icons'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSql',
        # stdlib
        'sqlite3', '_sqlite3',
        # app.core
        'app.core.colors', 'app.core.config', 'app.core.database',
        'app.core.demo_data', 'app.core.i18n', 'app.core.icon_utils',
        'app.core.scan_config', 'app.core.theme',
        # app.models
        'app.models.category', 'app.models.item', 'app.models.phone_model',
        'app.models.product', 'app.models.scan_session', 'app.models.transaction',
        # app.repositories
        'app.repositories.base', 'app.repositories.category_repo',
        'app.repositories.item_repo', 'app.repositories.model_repo',
        'app.repositories.product_repo', 'app.repositories.transaction_repo',
        # app.services
        'app.services.alert_service', 'app.services.scan_session_service',
        'app.services.stock_service',
        # app.ui
        'app.ui.main_window', 'app.ui.delegates',
        'app.ui.components.matrix_widget',
        'app.ui.tabs.base_tab', 'app.ui.tabs.matrix_tab',
        'app.ui.dialogs.product_dialogs', 'app.ui.dialogs.matrix_dialogs',
        'app.ui.dialogs.setup_wizard', 'app.ui.dialogs.barcode_assign_dialog',
        'app.ui.dialogs.admin.admin_dialog',
        'app.ui.dialogs.admin.shop_settings_panel',
        'app.ui.dialogs.admin.categories_panel',
        'app.ui.dialogs.admin.part_types_panel',
        'app.ui.dialogs.admin.models_panel',
        'app.ui.dialogs.admin.color_picker_widget',
        'app.ui.dialogs.admin.scan_settings_panel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'Pillow'],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='files/img/icon_logo.ico',
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
