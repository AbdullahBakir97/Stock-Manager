# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Stock Manager Pro v2.3
# Build: cd src && pyinstaller StockManagerPro.spec --noconfirm --clean

import glob, os
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_all, collect_submodules

pil_datas, pil_binaries, pil_hiddenimports     = collect_all('PIL')
barcode_datas, barcode_binaries, barcode_hiddenimports = collect_all('barcode')
fpdf_datas, fpdf_binaries, fpdf_hiddenimports  = collect_all('fpdf')
fitz_datas, fitz_binaries, fitz_hiddenimports  = collect_all('fitz')

# Force-collect PIL .pyd files (Python 3.11+ suffix confuses PyInstaller)
import PIL
pil_dir = os.path.dirname(PIL.__file__)
pil_pyd_files = [(f, 'PIL') for f in glob.glob(os.path.join(pil_dir, '*.pyd'))]
pil_binaries = pil_binaries + pil_pyd_files

block_cipher = None

a = Analysis(
    ['files/main.py'],
    pathex=['files'],
    binaries=collect_dynamic_libs('PyQt6') + pil_binaries + barcode_binaries + fpdf_binaries + fitz_binaries,
    datas=[
        ('files/img/icon_logo.ico', 'img'),
        ('files/img/logo.png',      'img'),
        ('files/img/icons',         'img/icons'),
    ] + pil_datas + barcode_datas + fpdf_datas + fitz_datas,
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSql',
        # stdlib
        'sqlite3', '_sqlite3',
    ] + pil_hiddenimports + barcode_hiddenimports + fpdf_hiddenimports + fitz_hiddenimports + [
        # ── app.core ──────────────────────────────────────────────────────────
        'app.core.colors',
        'app.core.config',
        'app.core.database',
        'app.core.demo_data',
        'app.core.health',
        'app.core.i18n',
        'app.core.icon_utils',
        'app.core.logger',
        'app.core.scan_config',
        'app.core.theme',
        'app.core.version',
        # ── app.models ────────────────────────────────────────────────────────
        'app.models.audit',
        'app.models.category',
        'app.models.customer',
        'app.models.item',
        'app.models.location',
        'app.models.phone_model',
        'app.models.price_list',
        'app.models.purchase_order',
        'app.models.return_item',
        'app.models.sale',
        'app.models.scan_session',
        'app.models.supplier',
        'app.models.transaction',
        # ── app.repositories ──────────────────────────────────────────────────
        'app.repositories.audit_repo',
        'app.repositories.base',
        'app.repositories.category_repo',
        'app.repositories.customer_repo',
        'app.repositories.item_repo',
        'app.repositories.location_repo',
        'app.repositories.model_repo',
        'app.repositories.price_list_repo',
        'app.repositories.purchase_order_repo',
        'app.repositories.return_repo',
        'app.repositories.sale_repo',
        'app.repositories.supplier_repo',
        'app.repositories.transaction_repo',
        # ── app.services ──────────────────────────────────────────────────────
        'app.services.alert_service',
        'app.services.audit_service',
        'app.services.backup_scheduler',
        'app.services.backup_service',
        'app.services.barcode_gen_service',
        'app.services.customer_service',
        'app.services.export_service',
        'app.services.image_service',
        'app.services.import_service',
        'app.services.location_service',
        'app.services.price_list_service',
        'app.services.purchase_order_service',
        'app.services.receipt_service',
        'app.services.report_service',
        'app.services.return_service',
        'app.services.sale_service',
        'app.services.scan_session_service',
        'app.services.stock_service',
        'app.services.supplier_service',
        'app.services.undo_service',
        'app.services.update_service',
        # ── app.ui.components ─────────────────────────────────────────────────
        'app.ui.components.barcode_line_edit',
        'app.ui.components.charts',
        'app.ui.components.collapsible_section',
        'app.ui.components.dashboard_widget',
        'app.ui.components.empty_state',
        'app.ui.components.filter_bar',
        'app.ui.components.footer_bar',
        'app.ui.components.header_bar',
        'app.ui.components.language_switcher',
        'app.ui.components.loading_overlay',
        'app.ui.components.matrix_widget',
        'app.ui.components.mini_txn_list',
        'app.ui.components.notification_panel',
        'app.ui.components.product_detail',
        'app.ui.components.product_detail_bar',
        'app.ui.components.product_table',
        'app.ui.components.responsive_table',
        'app.ui.components.sidebar',
        'app.ui.components.splash_screen',
        'app.ui.components.theme_toggle',
        'app.ui.components.toast',
        'app.ui.components.transaction_table',
        'app.ui.components.update_banner',
        # ── app.ui.controllers ────────────────────────────────────────────────
        'app.ui.controllers.alert_controller',
        'app.ui.controllers.bulk_ops',
        'app.ui.controllers.inventory_ops',
        'app.ui.controllers.nav_controller',
        'app.ui.controllers.startup_controller',
        'app.ui.controllers.stock_ops',
        'app.ui.controllers.update_controller',
        # ── app.ui.pages ──────────────────────────────────────────────────────
        'app.ui.pages.analytics_page',
        'app.ui.pages.audit_page',
        'app.ui.pages.barcode_gen_page',
        'app.ui.pages.inventory_page',
        'app.ui.pages.price_lists_page',
        'app.ui.pages.purchase_orders_page',
        'app.ui.pages.reports_page',
        'app.ui.pages.returns_page',
        'app.ui.pages.sales_page',
        'app.ui.pages.suppliers_page',
        'app.ui.pages.transactions_page',
        # ── app.ui.tabs ───────────────────────────────────────────────────────
        'app.ui.tabs.base_tab',
        'app.ui.tabs.matrix_tab',
        'app.ui.tabs.quick_scan_tab',
        'app.ui.tabs.stock_ops_tab',
        # ── app.ui.dialogs ────────────────────────────────────────────────────
        'app.ui.dialogs.admin.about_panel',
        'app.ui.dialogs.admin.admin_dialog',
        'app.ui.dialogs.admin.backup_panel',
        'app.ui.dialogs.admin.categories_panel',
        'app.ui.dialogs.admin.color_picker_widget',
        'app.ui.dialogs.admin.customers_panel',
        'app.ui.dialogs.admin.db_tools_panel',
        'app.ui.dialogs.admin.import_export_panel',
        'app.ui.dialogs.admin.locations_panel',
        'app.ui.dialogs.admin.models_panel',
        'app.ui.dialogs.admin.part_types_panel',
        'app.ui.dialogs.admin.scan_settings_panel',
        'app.ui.dialogs.admin.shop_settings_panel',
        'app.ui.dialogs.admin.suppliers_panel',
        'app.ui.dialogs.barcode_assign_dialog',
        'app.ui.dialogs.bulk_price_dialog',
        'app.ui.dialogs.dialog_base',
        'app.ui.dialogs.help_dialog',
        'app.ui.dialogs.matrix_dialogs',
        'app.ui.dialogs.price_list_dialogs',
        'app.ui.dialogs.product_dialogs',
        'app.ui.dialogs.setup_wizard',
        # ── app.ui.workers ────────────────────────────────────────────────────
        'app.ui.workers.data_worker',
        'app.ui.workers.update_worker',
        'app.ui.workers.worker_pool',
        # ── app.ui (misc) ─────────────────────────────────────────────────────
        'app.ui.delegates',
        'app.ui.helpers',
        'app.ui.main_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
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
    version_file='../installer/file_version_info.txt',
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
