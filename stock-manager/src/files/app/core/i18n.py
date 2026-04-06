"""
i18n.py — Translations for Stock Manager Pro
Languages: EN (English), DE (German), AR (Arabic — RTL)
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

LANG: str = "EN"

_TR: dict[str, dict[str, str]] = {
    # ── App ──────────────────────────────────────────────────────────────────
    "app_title": {
        "EN": "Stock Manager Pro",
        "DE": "Lagerverwaltung Pro",
        "AR": "مدير المخزون",
    },
    # ── Top bar ──────────────────────────────────────────────────────────────
    "alert_ok": {
        "EN": "●  All Stock OK",
        "DE": "●  Alle Bestände OK",
        "AR": "●  المخزون بخير",
    },
    "alert_critical": {
        "EN": "⚠  {n} Alert{s}  ·  OUT OF STOCK",
        "DE": "⚠  {n} Alarm{s}  ·  AUSVERKAUFT",
        "AR": "⚠  {n} تنبيه  ·  نفد المخزون",
    },
    "alert_warn": {
        "EN": "⚠  {n} Low Stock Alert{s}",
        "DE": "⚠  {n} Niedriger Bestand",
        "AR": "⚠  {n} تنبيه مخزون منخفض",
    },

    # ── Notification panel ────────────────────────────────────────────────────
    "notif_title":           {"EN": "Notifications ({n})",         "DE": "Benachrichtigungen ({n})",      "AR": "الإشعارات ({n})"},
    "notif_title_clear":     {"EN": "Notifications",               "DE": "Benachrichtigungen",            "AR": "الإشعارات"},
    "notif_all_clear":       {"EN": "You're all caught up!",       "DE": "Alles in Ordnung!",             "AR": "لا توجد إشعارات جديدة!"},
    "notif_sec_update":      {"EN": "Update Available",            "DE": "Update verfügbar",              "AR": "تحديث متاح"},
    "notif_sec_stock":       {"EN": "Stock Alerts",                "DE": "Lagerwarnung",                  "AR": "تنبيهات المخزون"},
    "notif_update_title":    {"EN": "v{version} is ready to install", "DE": "v{version} bereit zur Installation", "AR": "v{version} جاهز للتثبيت"},
    "notif_released":        {"EN": "Released {date}",             "DE": "Veröffentlicht {date}",         "AR": "تاريخ الإصدار {date}"},
    "notif_install_now":     {"EN": "⬇  Install Now",             "DE": "⬇  Jetzt installieren",         "AR": "⬇  تثبيت الآن"},
    "notif_remind_later":    {"EN": "Remind Later",                "DE": "Später erinnern",               "AR": "تذكيرني لاحقاً"},
    "notif_view_alerts":     {"EN": "View All Alerts",             "DE": "Alle Warnungen anzeigen",       "AR": "عرض جميع التنبيهات"},
    "notif_stock_expired":   {"EN": "{n} item(s) expired",         "DE": "{n} Artikel abgelaufen",        "AR": "{n} منتج منتهي الصلاحية"},
    "notif_stock_expiring":  {"EN": "{n} item(s) expiring soon",   "DE": "{n} Artikel läuft bald ab",     "AR": "{n} منتج ينتهي قريباً"},
    "notif_stock_low":       {"EN": "{n} item(s) low / out of stock", "DE": "{n} Artikel niedrig/ausverkauft", "AR": "{n} منتج منخفض/نفد"},
    "tooltip_refresh": {
        "EN": "Refresh  F5",
        "DE": "Aktualisieren  F5",
        "AR": "تحديث  F5",
    },
    "tooltip_theme": {
        "EN": "Toggle light / dark",
        "DE": "Hell / Dunkel umschalten",
        "AR": "تبديل الوضع",
    },
    # ── Summary cards ─────────────────────────────────────────────────────────
    "card_total_products": {
        "EN": "Total Products",
        "DE": "Produkte gesamt",
        "AR": "إجمالي المنتجات",
    },
    "card_total_units": {
        "EN": "Total Units",
        "DE": "Einheiten gesamt",
        "AR": "إجمالي الوحدات",
    },
    "card_low_stock": {
        "EN": "Low Stock",
        "DE": "Niedriger Bestand",
        "AR": "مخزون منخفض",
    },
    "card_out_of_stock": {
        "EN": "Out of Stock",
        "DE": "Ausverkauft",
        "AR": "نفد المخزون",
    },
    "card_inventory_value": {
        "EN": "Inventory Value",
        "DE": "Lagerwert",
        "AR": "قيمة المخزون",
    },
    # ── Dashboard ─────────────────────────────────────────────────────────────
    "dash_inventory_value": {
        "EN": "Inventory Value",
        "DE": "Inventarwert",
        "AR": "قيمة المخزون",
    },
    "dash_quick_actions": {
        "EN": "Quick Actions",
        "DE": "Schnellaktionen",
        "AR": "إجراءات سريعة",
    },
    "dash_new_product": {
        "EN": "New Product",
        "DE": "Neues Produkt",
        "AR": "منتج جديد",
    },
    "dash_stock_in": {
        "EN": "Stock In",
        "DE": "Eingang",
        "AR": "إدخال مخزون",
    },
    "dash_stock_out": {
        "EN": "Stock Out",
        "DE": "Ausgang",
        "AR": "إخراج مخزون",
    },
    "dash_export_csv": {
        "EN": "Export CSV",
        "DE": "CSV Export",
        "AR": "تصدير CSV",
    },
    # ── Toolbar ────────────────────────────────────────────────────────────────
    "search_placeholder": {
        "EN": "  Search or scan barcode…",
        "DE": "  Suchen oder Barcode scannen…",
        "AR": "  ابحث أو امسح الباركود…",
    },
    "low_stock_only": {
        "EN": "Low stock only",
        "DE": "Nur niedriger Bestand",
        "AR": "المخزون المنخفض فقط",
    },
    "btn_new_product": {
        "EN": "＋  New Product",
        "DE": "＋  Neues Produkt",
        "AR": "＋  منتج جديد",
    },
    # ── Tabs ──────────────────────────────────────────────────────────────────
    "tab_products": {
        "EN": "  Inventory  ",
        "DE": "  Inventar  ",
        "AR": "  المخزون  ",
    },
    "tab_transactions": {
        "EN": "  All Transactions  ",
        "DE": "  Alle Transaktionen  ",
        "AR": "  جميع المعاملات  ",
    },
    "txn_history_caption": {
        "EN": "Complete movement history  ·  last 500 records",
        "DE": "Vollständige Bewegungshistorie  ·  letzte 500 Einträge",
        "AR": "سجل الحركة الكامل  ·  آخر 500 سجل",
    },
    "btn_refresh": {
        "EN": "↺  Refresh",
        "DE": "↺  Aktualisieren",
        "AR": "↺  تحديث",
    },
    # ── Product table columns ─────────────────────────────────────────────────
    "col_num":     {"EN": "#",        "DE": "#",               "AR": "#"},
    "col_brand":   {"EN": "Brand",    "DE": "Marke",           "AR": "العلامة"},
    "col_type":    {"EN": "Type",     "DE": "Typ",             "AR": "النوع"},
    "col_color":   {"EN": "Color",    "DE": "Farbe",           "AR": "اللون"},
    "col_barcode": {"EN": "Barcode",  "DE": "Barcode",         "AR": "الباركود"},
    "col_stock":   {"EN": "Stock",    "DE": "Bestand",         "AR": "المخزون"},
    "col_alert":   {"EN": "Alert ≤",  "DE": "Alarm ≤",         "AR": "تنبيه ≤"},
    "col_status":  {"EN": "Status",   "DE": "Status",          "AR": "الحالة"},
    "col_price":   {"EN": "Price",    "DE": "Preis",           "AR": "السعر"},
    "col_item":    {"EN": "Item",     "DE": "Artikel",         "AR": "العنصر"},
    "col_min":     {"EN": "Min",      "DE": "Min",             "AR": "الحد الأدنى"},
    "col_actions": {"EN": "Actions",  "DE": "Aktionen",        "AR": "إجراءات"},
    # ── Transaction table columns ─────────────────────────────────────────────
    "txn_col_item":  {"EN": "Item",        "DE": "Artikel",         "AR": "العنصر"},
    "col_datetime":  {"EN": "Date & Time", "DE": "Datum & Zeit",    "AR": "التاريخ والوقت"},
    "col_operation": {"EN": "Operation",   "DE": "Vorgang",         "AR": "العملية"},
    "col_delta":     {"EN": "Δ Qty",       "DE": "Δ Menge",         "AR": "Δ الكمية"},
    "col_before":    {"EN": "Before",      "DE": "Vorher",          "AR": "قبل"},
    "col_after_col": {"EN": "After",       "DE": "Nachher",         "AR": "بعد"},
    "col_note":      {"EN": "Note",        "DE": "Notiz",           "AR": "ملاحظة"},
    # ── Status badge labels ───────────────────────────────────────────────────
    "status_ok_lbl":       {"EN": "OK",       "DE": "OK",       "AR": "موافق"},
    "status_low_lbl":      {"EN": "LOW",      "DE": "NIEDRIG",  "AR": "منخفض"},
    "status_critical_lbl": {"EN": "CRITICAL", "DE": "KRITISCH", "AR": "حرج"},
    "status_out_lbl":      {"EN": "OUT",      "DE": "LEER",     "AR": "نفد"},
    # ── Detail panel ─────────────────────────────────────────────────────────
    "detail_select_prompt": {
        "EN": "Select a product",
        "DE": "Produkt auswählen",
        "AR": "اختر منتجاً",
    },
    "detail_barcode": {
        "EN": "Barcode: {val}",
        "DE": "Barcode: {val}",
        "AR": "الباركود: {val}",
    },
    "detail_updated": {
        "EN": "Updated: {val}",
        "DE": "Aktualisiert: {val}",
        "AR": "تحديث: {val}",
    },
    "detail_current_stock": {
        "EN": "CURRENT STOCK",
        "DE": "AKTUELLER BESTAND",
        "AR": "المخزون الحالي",
    },
    "detail_alert_at": {
        "EN": "Alert at ≤ {n} units",
        "DE": "Alarm bei ≤ {n} Einh.",
        "AR": "تنبيه عند ≤ {n} وحدة",
    },
    "detail_operations": {
        "EN": "OPERATIONS",
        "DE": "VORGÄNGE",
        "AR": "العمليات",
    },
    "detail_recent_txns": {
        "EN": "RECENT TRANSACTIONS",
        "DE": "LETZTE TRANSAKTIONEN",
        "AR": "المعاملات الأخيرة",
    },
    "detail_category": {
        "EN": "Category: {val}",
        "DE": "Kategorie: {val}",
        "AR": "الفئة: {val}",
    },
    "detail_part_type": {
        "EN": "Type: {val}",
        "DE": "Typ: {val}",
        "AR": "النوع: {val}",
    },
    "detail_sku": {
        "EN": "SKU: {val}",
        "DE": "SKU: {val}",
        "AR": "SKU: {val}",
    },
    "detail_stock_trend": {
        "EN": "STOCK TREND",
        "DE": "BESTANDSTREND",
        "AR": "اتجاه المخزون",
    },
    "detail_no_barcode": {
        "EN": "No barcode assigned",
        "DE": "Kein Barcode zugewiesen",
        "AR": "لا يوجد باركود",
    },
    "btn_edit":      {"EN": "Edit",        "DE": "Bearbeiten", "AR": "تعديل"},
    "btn_delete":    {"EN": "Delete",      "DE": "Löschen",    "AR": "حذف"},
    "btn_stock_in":  {"EN": "  \u2191   Stock In",   "DE": "  \u2191   Eingang",   "AR": "  \u2191   إضافة"},
    "btn_stock_out": {"EN": "  \u2193   Stock Out",  "DE": "  \u2193   Ausgang",   "AR": "  \u2193   سحب"},
    "btn_adjust":    {"EN": "  \u21C4   Adjust",     "DE": "  \u21C4   Anpassen",  "AR": "  \u21C4   ضبط"},
    # ── Detail badge labels ───────────────────────────────────────────────────
    "badge_ok":       {"EN": "✓  OK",          "DE": "✓  OK",           "AR": "✓  موافق"},
    "badge_low":      {"EN": "⚠  LOW",          "DE": "⚠  NIEDRIG",     "AR": "⚠  منخفض"},
    "badge_critical": {"EN": "⚡  CRITICAL",     "DE": "⚡  KRITISCH",    "AR": "⚡  حرج"},
    "badge_out":      {"EN": "✕  OUT OF STOCK", "DE": "✕  AUSVERKAUFT", "AR": "✕  نفد المخزون"},
    # ── Mini transaction list ─────────────────────────────────────────────────
    "no_transactions": {
        "EN": "No transactions yet",
        "DE": "Noch keine Transaktionen",
        "AR": "لا توجد معاملات بعد",
    },
    # ── Operation short labels (used in mini txn list badges) ─────────────────
    "op_in_short":     {"EN": "IN",  "DE": "EIN",  "AR": "دخول"},
    "op_out_short":    {"EN": "OUT", "DE": "AUS",  "AR": "خروج"},
    "op_adj_short":    {"EN": "ADJ", "DE": "ANP",  "AR": "ضبط"},
    "op_create_short": {"EN": "NEW", "DE": "NEU",  "AR": "جديد"},
    # ── Loading / startup ─────────────────────────────────────────────────────
    "loading_dashboard":  {"EN": "Loading dashboard…",  "DE": "Dashboard laden…",    "AR": "جارٍ تحميل لوحة التحكم…"},
    "loading_inventory":  {"EN": "Loading inventory…",  "DE": "Inventar laden…",     "AR": "جارٍ تحميل المخزون…"},
    "startup_db":         {"EN": "Initialising database…",  "DE": "Datenbank initialisieren…", "AR": "تهيئة قاعدة البيانات…"},
    "startup_config":     {"EN": "Loading configuration…",  "DE": "Konfiguration laden…",      "AR": "تحميل الإعدادات…"},
    "startup_ui":         {"EN": "Building interface…",     "DE": "Oberfläche aufbauen…",       "AR": "بناء الواجهة…"},
    "startup_ready":      {"EN": "Ready!",                  "DE": "Bereit!",                    "AR": "جاهز!"},
    # ── Auto-Update ───────────────────────────────────────────────────────────
    "update_available":      {"EN": "Update available",         "DE": "Update verfügbar",              "AR": "تحديث متاح"},
    "update_available_body": {"EN": "Version {version} is ready. {notes}", "DE": "Version {version} ist bereit. {notes}", "AR": "الإصدار {version} جاهز. {notes}"},
    "update_now":            {"EN": "Download & Install",       "DE": "Herunterladen & Installieren",  "AR": "تحميل وتثبيت"},
    "update_later":          {"EN": "Remind Me Later",          "DE": "Später erinnern",               "AR": "ذكرني لاحقاً"},
    "update_dismiss":        {"EN": "Skip This Version",        "DE": "Diese Version überspringen",    "AR": "تخطي هذا الإصدار"},
    "update_downloading":    {"EN": "Downloading update…",      "DE": "Update wird heruntergeladen…",  "AR": "جارٍ تحميل التحديث…"},
    "update_download_done":  {"EN": "Download complete. Launch installer?", "DE": "Download abgeschlossen. Installer starten?", "AR": "اكتمل التحميل. تشغيل برنامج التثبيت؟"},
    "update_install_now":    {"EN": "Install Now",              "DE": "Jetzt installieren",            "AR": "تثبيت الآن"},
    "update_install_later":  {"EN": "Later",                   "DE": "Später",                        "AR": "لاحقاً"},
    "update_error":          {"EN": "Update check failed",      "DE": "Update-Prüfung fehlgeschlagen", "AR": "فشل فحص التحديث"},
    "update_download_fail":  {"EN": "Download failed: {reason}","DE": "Download fehlgeschlagen: {reason}", "AR": "فشل التحميل: {reason}"},
    "update_checksum_fail":  {"EN": "Installer verification failed — download may be corrupted.", "DE": "Installer-Prüfung fehlgeschlagen.", "AR": "فشل التحقق من المثبت."},
    "update_current":        {"EN": "App is up to date",        "DE": "App ist aktuell",               "AR": "التطبيق محدّث"},

    # ── About & Updates panel ─────────────────────────────────────────────────
    # ── About panel — identity ────────────────────────────────────────────────
    "admin_tab_about":          {"EN": "About & Updates",         "DE": "Info & Updates",              "AR": "حول التطبيق"},
    "about_tagline":            {"EN": "Professional Inventory Management for Windows",
                                 "DE": "Professionelle Inventarverwaltung für Windows",
                                 "AR": "إدارة مخزون احترافية لنظام ويندوز"},
    "about_badge_stable":       {"EN": "STABLE",                  "DE": "STABIL",                      "AR": "مستقر"},
    "about_version":            {"EN": "Version",                 "DE": "Version",                     "AR": "الإصدار"},
    "about_license":            {"EN": "License",                 "DE": "Lizenz",                      "AR": "الترخيص"},
    "about_license_value":      {"EN": "Commercial — All Rights Reserved",
                                 "DE": "Kommerziell — Alle Rechte vorbehalten",
                                 "AR": "تجاري — جميع الحقوق محفوظة"},
    "about_copyright":          {"EN": "Copyright",               "DE": "Copyright",                   "AR": "حقوق النشر"},
    # ── About panel — system info ─────────────────────────────────────────────
    "about_sysinfo_title":      {"EN": "System Information",      "DE": "Systeminformationen",         "AR": "معلومات النظام"},
    "about_sysinfo_os":         {"EN": "Operating System",        "DE": "Betriebssystem",              "AR": "نظام التشغيل"},
    "about_sysinfo_python":     {"EN": "Python",                  "DE": "Python",                      "AR": "بايثون"},
    "about_sysinfo_db":         {"EN": "Database",                "DE": "Datenbank",                   "AR": "قاعدة البيانات"},
    "about_sysinfo_schema":     {"EN": "schema v{v}",             "DE": "Schema v{v}",                 "AR": "مخطط v{v}"},
    "about_sysinfo_datadir":    {"EN": "Data Directory",          "DE": "Datenverzeichnis",            "AR": "مجلد البيانات"},
    "about_copy_sysinfo":       {"EN": "Copy System Info",        "DE": "Systeminfo kopieren",         "AR": "نسخ معلومات النظام"},
    "about_open_datafolder":    {"EN": "Open Data Folder",        "DE": "Datenordner öffnen",          "AR": "فتح مجلد البيانات"},
    "about_copied":             {"EN": "✅ Copied to clipboard",   "DE": "✅ In Zwischenablage kopiert", "AR": "✅ تم النسخ"},
    # ── About panel — updates ─────────────────────────────────────────────────
    "about_updates_title":      {"EN": "Software Updates",        "DE": "Software-Updates",            "AR": "تحديثات البرنامج"},
    "about_auto_check":         {"EN": "Automatically check for updates at startup",
                                 "DE": "Beim Start automatisch auf Updates prüfen",
                                 "AR": "التحقق التلقائي من التحديثات عند بدء التشغيل"},
    "about_last_checked":       {"EN": "Last checked:",           "DE": "Zuletzt geprüft:",            "AR": "آخر فحص:"},
    "about_never_checked":      {"EN": "Never",                   "DE": "Noch nie",                    "AR": "لم يتم بعد"},
    "about_manifest_url":       {"EN": "Manifest URL:",           "DE": "Manifest-URL:",               "AR": "رابط البيان:"},
    "about_manifest_none":      {"EN": "Not configured",          "DE": "Nicht konfiguriert",          "AR": "غير مضبوط"},
    "about_check_now":          {"EN": "Check for Updates",       "DE": "Auf Updates prüfen",          "AR": "التحقق من التحديثات"},
    "about_checking":           {"EN": "Checking…",               "DE": "Prüfe…",                      "AR": "جارٍ التحقق…"},
    "about_preview_banner":     {"EN": "Preview Update Banner",   "DE": "Update-Banner anzeigen",      "AR": "معاينة شريط التحديث"},
    "about_preview_tip":        {"EN": "Closes settings and shows the animated update notification.",
                                 "DE": "Schließt Einstellungen und zeigt die Benachrichtigung.",
                                 "AR": "يغلق الإعدادات ويعرض إشعار التحديث المتحرك."},
    "about_check_idle":         {"EN": "Click 'Check for Updates' to check now.",
                                 "DE": "Klicke 'Auf Updates prüfen' um jetzt zu prüfen.",
                                 "AR": "اضغط 'التحقق من التحديثات' للفحص الآن."},
    "about_update_found":       {"EN": "🎉 Update v{version} is available!",
                                 "DE": "🎉 Update v{version} ist verfügbar!",
                                 "AR": "🎉 التحديث v{version} متاح!"},
    "about_up_to_date":         {"EN": "✅ You're on the latest version.",
                                 "DE": "✅ Du verwendest die neueste Version.",
                                 "AR": "✅ أنت تستخدم أحدث إصدار."},
    "about_check_error":        {"EN": "⚠️ Check failed: {reason}",
                                 "DE": "⚠️ Prüfung fehlgeschlagen: {reason}",
                                 "AR": "⚠️ فشل التحقق: {reason}"},
    # ── About panel — support ─────────────────────────────────────────────────
    "about_support_title":      {"EN": "Support & Resources",     "DE": "Support & Ressourcen",        "AR": "الدعم والموارد"},
    "about_btn_docs":           {"EN": "Documentation",           "DE": "Dokumentation",               "AR": "التوثيق"},
    "about_btn_changelog":      {"EN": "Changelog",               "DE": "Änderungsprotokoll",          "AR": "سجل التغييرات"},
    "about_btn_bug":            {"EN": "Report a Bug",            "DE": "Fehler melden",               "AR": "الإبلاغ عن خطأ"},
    "about_btn_feedback":       {"EN": "Send Feedback",           "DE": "Feedback senden",             "AR": "إرسال ملاحظة"},
    # ── Status bar ────────────────────────────────────────────────────────────
    "statusbar_ready": {
        "EN": "Ready  ·  Ctrl+N New  ·  Ctrl+I Stock In  ·  Ctrl+O Stock Out  ·  F5 Refresh",
        "DE": "Bereit  ·  Ctrl+N Neu  ·  Ctrl+I Eingang  ·  Ctrl+O Ausgang  ·  F5 Aktualisieren",
        "AR": "جاهز  ·  Ctrl+N جديد  ·  Ctrl+I إضافة  ·  Ctrl+O سحب  ·  F5 تحديث",
    },
    "status_n_products":      {"EN": "{n} product(s)",          "DE": "{n} Produkt(e)",           "AR": "{n} منتج"},
    "status_refreshed":       {"EN": "Refreshed",               "DE": "Aktualisiert",             "AR": "تم التحديث"},
    "status_product_added":   {"EN": "Product added — ID {pid}","DE": "Produkt hinzugefügt — ID {pid}", "AR": "تمت الإضافة — ID {pid}"},
    "status_product_updated": {"EN": "Product updated",         "DE": "Produkt aktualisiert",     "AR": "تم التحديث"},
    "status_product_deleted": {"EN": "Product deleted",         "DE": "Produkt gelöscht",         "AR": "تم الحذف"},
    "status_scanned":         {"EN": "Scanned → {brand} / {type}", "DE": "Gescannt → {brand} / {type}", "AR": "تم المسح → {brand} / {type}"},
    "status_unknown_bc":      {"EN": "Unknown barcode: {bc}",   "DE": "Unbekannter Barcode: {bc}","AR": "باركود غير معروف: {bc}"},
    "status_stock_op":        {"EN": "Stock {op}: {before} → {after}", "DE": "Bestand {op}: {before} → {after}", "AR": "المخزون {op}: {before} → {after}"},
    "status_quick_in":        {"EN": "Stock +1 applied", "DE": "Bestand +1 angewendet", "AR": "تم إضافة +1"},
    "status_quick_out":       {"EN": "Stock -1 applied", "DE": "Bestand -1 angewendet", "AR": "تم إخراج -1"},
    # ── Message boxes ─────────────────────────────────────────────────────────
    "msg_unknown_bc_title": {"EN": "Unknown Barcode",   "DE": "Unbekannter Barcode",     "AR": "باركود غير معروف"},
    "msg_unknown_bc_body": {
        "EN": "Barcode <b>{bc}</b> not found.<br>Create a new product with this barcode?",
        "DE": "Barcode <b>{bc}</b> nicht gefunden.<br>Neues Produkt mit diesem Barcode erstellen?",
        "AR": "الباركود <b>{bc}</b> غير موجود.<br>هل تريد إنشاء منتج جديد؟",
    },
    "msg_delete_title": {"EN": "Delete Product",    "DE": "Produkt löschen",         "AR": "حذف المنتج"},
    "msg_delete_body": {
        "EN": "Delete <b>{brand} / {type} / {color}</b> and all history?<br><span style='color:{red}'>Cannot be undone.</span>",
        "DE": "<b>{brand} / {type} / {color}</b> und alle Daten löschen?<br><span style='color:{red}'>Nicht rückgängig zu machen.</span>",
        "AR": "حذف <b>{brand} / {type} / {color}</b> وكل السجل؟<br><span style='color:{red}'>لا يمكن التراجع.</span>",
    },
    "msg_not_found_title": {"EN": "Not Found",       "DE": "Nicht gefunden",          "AR": "غير موجود"},
    "msg_not_found_body":  {"EN": "Product no longer exists.", "DE": "Produkt existiert nicht mehr.", "AR": "المنتج لم يعد موجوداً."},
    "msg_low_title":       {"EN": "⚠  {level}",      "DE": "⚠  {level}",              "AR": "⚠  {level}"},
    "msg_low_body": {
        "EN": "<b>{brand} / {type} / {color}</b><br>Stock: <b style='font-size:14pt'>{stock}</b> units — at or below threshold of <b>{thr}</b>.",
        "DE": "<b>{brand} / {type} / {color}</b><br>Bestand: <b style='font-size:14pt'>{stock}</b> Einh. — Grenzwert <b>{thr}</b> erreicht.",
        "AR": "<b>{brand} / {type} / {color}</b><br>المخزون: <b style='font-size:14pt'>{stock}</b> — الحد <b>{thr}</b>.",
    },
    "msg_level_out":  {"EN": "OUT OF STOCK",       "DE": "AUSVERKAUFT",             "AR": "نفد المخزون"},
    "msg_level_low":  {"EN": "LOW STOCK",          "DE": "NIEDRIGER BESTAND",       "AR": "مخزون منخفض"},
    "msg_op_failed":  {"EN": "Operation Failed",   "DE": "Vorgang fehlgeschlagen",  "AR": "فشلت العملية"},
    "msg_error":      {"EN": "Error",              "DE": "Fehler",                  "AR": "خطأ"},
    # ── Color picker dialog ────────────────────────────────────────────────────
    "dlg_choose_color":    {"EN": "Choose Color",      "DE": "Farbe wählen",            "AR": "اختر اللون"},
    "dlg_color_none":      {"EN": "None",              "DE": "Keine",                   "AR": "لا يوجد"},
    "dlg_color_select":    {"EN": "Select",            "DE": "Auswählen",               "AR": "اختر"},
    "dlg_color_no_title":  {"EN": "No Color",          "DE": "Keine Farbe",             "AR": "لا لون"},
    "dlg_color_no_body":   {"EN": "Please select a color.", "DE": "Bitte eine Farbe auswählen.", "AR": "يرجى اختيار لون."},
    "dlg_color_choose_btn":{"EN": "  Choose Color…",  "DE": "  Farbe wählen…",         "AR": "  اختر لوناً…"},
    # ── Product dialog ─────────────────────────────────────────────────────────
    "dlg_new_product":    {"EN": "New Product",      "DE": "Neues Produkt",            "AR": "منتج جديد"},
    "dlg_edit_product":   {"EN": "Edit Product",     "DE": "Produkt bearbeiten",       "AR": "تعديل المنتج"},
    "dlg_grp_identity":   {"EN": "Identity",         "DE": "Stammdaten",               "AR": "البيانات"},
    "dlg_grp_stock":      {"EN": "Stock Settings",   "DE": "Bestandseinstellungen",    "AR": "إعدادات المخزون"},
    "dlg_grp_dates":      {"EN": "Dates",            "DE": "Daten",                    "AR": "التواريخ"},
    "dlg_lbl_brand":      {"EN": "Brand *",          "DE": "Marke *",                  "AR": "العلامة *"},
    "dlg_lbl_type":       {"EN": "Type *",           "DE": "Typ *",                    "AR": "النوع *"},
    "dlg_lbl_color":      {"EN": "Color",             "DE": "Farbe",                    "AR": "اللون"},
    "dlg_lbl_barcode":    {"EN": "Barcode",          "DE": "Barcode",                  "AR": "الباركود"},
    "dlg_lbl_init_stock": {"EN": "Initial Stock",   "DE": "Anfangsbestand",            "AR": "المخزون الأولي"},
    "dlg_lbl_alert_when": {"EN": "Alert when ≤",    "DE": "Alarm wenn ≤",              "AR": "تنبيه عند ≤"},
    "dlg_lbl_sell_price": {"EN": "Sell Price",       "DE": "Verkaufspreis",             "AR": "سعر البيع"},
    "dlg_ph_sell_price":  {"EN": "0.00  (optional)", "DE": "0.00  (optional)",          "AR": "0.00  (اختياري)"},
    "detail_sell_price":  {"EN": "Price: {val}",     "DE": "Preis: {val}",              "AR": "السعر: {val}"},
    "dlg_save_product":   {"EN": "Save Product",    "DE": "Produkt speichern",         "AR": "حفظ"},
    "dlg_ph_brand":       {"EN": "e.g. Nike, Apple…","DE": "z.B. Nike, Apple…",        "AR": "مثال: Nike, Apple…"},
    "dlg_ph_type":        {"EN": "e.g. Shoes, Phone…","DE": "z.B. Schuhe, Telefon…",  "AR": "مثال: أحذية, هاتف…"},
    "dlg_ph_barcode":     {"EN": "Scan or type — optional", "DE": "Scannen oder eingeben — optional", "AR": "امسح أو اكتب — اختياري"},
    "dlg_required_title": {"EN": "Required",         "DE": "Pflichtfeld",              "AR": "مطلوب"},
    "dlg_field_empty":    {"EN": "{field} cannot be empty.", "DE": "{field} darf nicht leer sein.", "AR": "{field} لا يمكن أن يكون فارغاً."},
    # ── Stock op dialog ────────────────────────────────────────────────────────
    "op_stock_in":    {"EN": "Stock In",          "DE": "Wareneingang",             "AR": "إضافة مخزون"},
    "op_stock_out":   {"EN": "Stock Out",         "DE": "Warenausgang",             "AR": "سحب مخزون"},
    "op_adjust":      {"EN": "Adjust Stock",      "DE": "Bestand anpassen",         "AR": "ضبط المخزون"},
    "op_confirm_in":  {"EN": "Confirm Stock In",  "DE": "Eingang bestätigen",       "AR": "تأكيد الإضافة"},
    "op_confirm_out": {"EN": "Confirm Stock Out", "DE": "Ausgang bestätigen",       "AR": "تأكيد السحب"},
    "op_confirm_adj": {"EN": "Confirm Adjustment","DE": "Anpassung bestätigen",     "AR": "تأكيد الضبط"},
    "op_current_stock":{"EN": "Current stock:",  "DE": "Aktueller Bestand:",        "AR": "المخزون الحالي:"},
    "op_alert_le":    {"EN": "Alert ≤ {thr}",    "DE": "Alarm ≤ {thr}",             "AR": "تنبيه ≤ {thr}"},
    "op_set_to":      {"EN": "Set stock to",     "DE": "Bestand setzen auf",        "AR": "ضبط المخزون على"},
    "op_quantity":    {"EN": "Quantity",          "DE": "Menge",                    "AR": "الكمية"},
    "op_note":        {"EN": "Note",              "DE": "Notiz",                    "AR": "ملاحظة"},
    "op_note_ph":     {"EN": "PO#, reason, reference…", "DE": "Bestellnr., Grund, Referenz…", "AR": "رقم الطلب، السبب…"},
    "op_cancel":      {"EN": "Cancel",            "DE": "Abbrechen",                "AR": "إلغاء"},
    "op_after":       {"EN": "After: ",           "DE": "Nachher: ",                "AR": "بعد: "},
    "op_invalid":     {"EN": "INVALID",           "DE": "UNGÜLTIG",                 "AR": "غير صالح"},
    "op_out_of_stock":{"EN": "OUT OF STOCK",      "DE": "AUSVERKAUFT",              "AR": "نفد المخزون"},
    "op_low_stock":   {"EN": "LOW STOCK",         "DE": "NIEDRIGER BESTAND",        "AR": "مخزون منخفض"},
    "op_ok":          {"EN": "OK",                "DE": "OK",                       "AR": "موافق"},
    "op_insuff_title":{"EN": "Insufficient Stock","DE": "Unzureichender Bestand",   "AR": "مخزون غير كافٍ"},
    "op_insuff_body": {
        "EN": "Cannot remove <b>{qty}</b>.<br>Available: <b>{cur}</b>",
        "DE": "<b>{qty}</b> kann nicht entnommen werden.<br>Verfügbar: <b>{cur}</b>",
        "AR": "لا يمكن إزالة <b>{qty}</b>.<br>المتاح: <b>{cur}</b>",
    },
    # ── Low stock alert dialog ─────────────────────────────────────────────────
    "dlg_alerts_title":  {"EN": "Low Stock Alerts",         "DE": "Bestandswarnungen",        "AR": "تنبيهات المخزون"},
    "dlg_alerts_header": {"EN": "⚠  Low Stock Alerts",      "DE": "⚠  Bestandswarnungen",     "AR": "⚠  تنبيهات المخزون المنخفض"},
    "col_threshold":     {"EN": "Threshold",                 "DE": "Grenzwert",                "AR": "الحد الأدنى"},
    "dlg_alerts_hint": {
        "EN": "Double-click a row to navigate to that product",
        "DE": "Doppelklick auf eine Zeile, um zum Produkt zu navigieren",
        "AR": "انقر مرتين على صف للانتقال للمنتج",
    },
    "btn_close": {"EN": "Close", "DE": "Schließen", "AR": "إغلاق"},
    # ── Known DB-stored note strings ──────────────────────────────────────────
    "note_product_created": {"EN": "Product created", "DE": "Produkt erstellt", "AR": "تم إنشاء المنتج"},

    # ── Displays tab ──────────────────────────────────────────────────────────
    "tab_displays": {
        "EN": "  Displays  ",
        "DE": "  Displays  ",
        "AR": "  الشاشات  ",
    },
    "disp_caption": {
        "EN": "Displays Inventory  —  double-click any cell to edit",
        "DE": "Displays-Bestand  —  Doppelklick zum Bearbeiten",
        "AR": "مخزون الشاشات  —  انقر مرتين على أي خلية للتعديل",
    },
    "disp_all_brands": {
        "EN": "All Brands",
        "DE": "Alle Marken",
        "AR": "جميع العلامات",
    },
    "disp_add_model": {
        "EN": "＋  Add Model",
        "DE": "＋  Modell hinzufügen",
        "AR": "＋  إضافة طراز",
    },
    "disp_legend_neg": {
        "EN": "Best-Bung negative → need to order",
        "DE": "Best-Bung negativ → bestellen",
        "AR": "Best-Bung سالب ← يحتاج طلب",
    },
    "disp_legend_zero": {
        "EN": "Best-Bung = 0 → at minimum",
        "DE": "Best-Bung = 0 → am Minimum",
        "AR": "Best-Bung = 0 ← عند الحد الأدنى",
    },
    "disp_legend_pos": {
        "EN": "Best-Bung positive → surplus",
        "DE": "Best-Bung positiv → Überschuss",
        "AR": "Best-Bung موجب ← فائض",
    },
    "disp_col_model": {
        "EN": "Model",
        "DE": "Modell",
        "AR": "الطراز",
    },
    "disp_col_stock": {
        "EN": "Stock",
        "DE": "Bestand",
        "AR": "المخزون",
    },
    # ── Stock op dialog ───────────────────────────────────────────────────────
    "disp_need_more": {
        "EN": "Need {n} more to reach minimum",
        "DE": "Brauche {n} mehr bis Minimum",
        "AR": "يحتاج {n} وحدة للحد الأدنى",
    },
    "disp_surplus": {
        "EN": "Surplus: {n} above minimum",
        "DE": "Überschuss: {n} über Minimum",
        "AR": "فائض: {n} فوق الحد الأدنى",
    },
    "disp_op_in":  {"EN": "＋  Stock IN",   "DE": "＋  Eingang",      "AR": "＋  إضافة"},
    "disp_op_out": {"EN": "－  Stock OUT",  "DE": "－  Ausgang",      "AR": "－  سحب"},
    "disp_op_set": {"EN": "＝  Set Exact",  "DE": "＝  Exakt setzen", "AR": "＝  ضبط دقيق"},
    "disp_qty_lbl":   {"EN": "Quantity:",        "DE": "Menge:",            "AR": "الكمية:"},
    "disp_exact_lbl": {"EN": "New exact stock:", "DE": "Neuer Bestand:",    "AR": "المخزون الجديد:"},
    "disp_stock_err": {"EN": "Stock Error",      "DE": "Bestandsfehler",    "AR": "خطأ في المخزون"},
    # ── Stamm-Zahl dialog ─────────────────────────────────────────────────────
    "disp_dlg_stamm": {
        "EN": "Set Stamm-Zahl",
        "DE": "Stamm-Zahl festlegen",
        "AR": "تحديد Stamm-Zahl",
    },
    "disp_stamm_hint": {
        "EN": "Stamm-Zahl is the minimum stock level.\nBest-Bung = Stock − Stamm-Zahl\n(negative = need to order, positive = surplus).",
        "DE": "Stamm-Zahl ist der Mindestbestand.\nBest-Bung = Bestand − Stamm-Zahl\n(negativ = bestellen, positiv = Überschuss).",
        "AR": "Stamm-Zahl هو الحد الأدنى للمخزون.\nBest-Bung = المخزون − Stamm-Zahl\n(سالب = يحتاج طلب، موجب = فائض).",
    },
    # ── Inventur dialog ───────────────────────────────────────────────────────
    "disp_dlg_inv": {
        "EN": "Set Order Amount",
        "DE": "Bestellmenge festlegen",
        "AR": "تحديد كمية الطلب",
    },
    "disp_sys_stock": {
        "EN": "Current stock: {n}",
        "DE": "Aktueller Bestand: {n}",
        "AR": "المخزون الحالي: {n}",
    },
    "disp_phys_count": {"EN": "Order amount:", "DE": "Bestellmenge:", "AR": "الكمية المطلوبة:"},
    # ── Tooltips ──────────────────────────────────────────────────────────────
    "disp_tip_stamm": {
        "EN": "Double-click to set Stamm-Zahl (minimum stock level)",
        "DE": "Doppelklick zum Festlegen des Mindestbestands",
        "AR": "انقر مرتين لتحديد الحد الأدنى للمخزون",
    },
    "disp_tip_stock": {
        "EN": "Double-click to add / remove stock",
        "DE": "Doppelklick zum Hinzufügen / Entfernen",
        "AR": "انقر مرتين لإضافة / سحب المخزون",
    },
    "disp_tip_inv": {
        "EN": "Double-click to set/clear order amount",
        "DE": "Doppelklick zum Setzen/Löschen der Bestellmenge",
        "AR": "انقر مرتين لتحديد/مسح كمية الطلب",
    },
    "disp_tip_bb_neg":  {"EN": "Need {n} more to reach Stamm-Zahl", "DE": "{n} mehr bis Stamm-Zahl", "AR": "يحتاج {n} لبلوغ Stamm-Zahl"},
    "disp_tip_bb_pos":  {"EN": "Surplus: {n} above Stamm-Zahl",     "DE": "Überschuss: {n}",         "AR": "فائض: {n} فوق Stamm-Zahl"},
    "disp_tip_bb_zero": {"EN": "Exactly at Stamm-Zahl",             "DE": "Genau am Stamm-Zahl",     "AR": "عند Stamm-Zahl تماماً"},
    # ── Add Model dialog ──────────────────────────────────────────────────────
    "disp_dlg_add_model": {
        "EN": "Add Phone Model",
        "DE": "Modell hinzufügen",
        "AR": "إضافة طراز هاتف",
    },
    "disp_lbl_brand": {
        "EN": "Brand *",
        "DE": "Marke *",
        "AR": "العلامة *",
    },
    "disp_lbl_model_name": {
        "EN": "Model Name *",
        "DE": "Modellname *",
        "AR": "اسم الطراز *",
    },
    "disp_ph_brand": {
        "EN": "e.g. Apple, Samsung…",
        "DE": "z.B. Apple, Samsung…",
        "AR": "مثال: Apple, Samsung…",
    },
    "disp_ph_model": {
        "EN": "e.g. iPhone 16 Pro, Galaxy S24 Ultra…",
        "DE": "z.B. iPhone 16 Pro, Galaxy S24 Ultra…",
        "AR": "مثال: iPhone 16 Pro, Galaxy S24 Ultra…",
    },
    "disp_save_model": {
        "EN": "Add Model",
        "DE": "Modell hinzufügen",
        "AR": "إضافة الطراز",
    },
    "disp_model_empty": {
        "EN": "Brand and Model Name cannot be empty.",
        "DE": "Marke und Modellname dürfen nicht leer sein.",
        "AR": "العلامة واسم الطراز لا يمكن أن يكونا فارغين.",
    },
    "disp_model_added": {
        "EN": "Model '{name}' added.",
        "DE": "Modell '{name}' hinzugefügt.",
        "AR": "تمت إضافة الطراز '{name}'.",
    },
    "disp_filter_brand": {
        "EN": "Brand:",
        "DE": "Marke:",
        "AR": "العلامة:",
    },
    # ── Admin dialog ─────────────────────────────────────────────────────────
    "admin_title": {
        "EN": "Admin Settings",
        "DE": "Admin-Einstellungen",
        "AR": "إعدادات الإدارة",
    },
    "admin_tab_shop": {
        "EN": "Shop Settings",
        "DE": "Shop-Einstellungen",
        "AR": "إعدادات المتجر",
    },
    "admin_tab_categories": {
        "EN": "Categories",
        "DE": "Kategorien",
        "AR": "الفئات",
    },
    "admin_tab_part_types": {
        "EN": "Part Types",
        "DE": "Teiletypen",
        "AR": "أنواع القطع",
    },
    "admin_tab_models": {
        "EN": "Models",
        "DE": "Modelle",
        "AR": "الطرازات",
    },
    # ── Shop settings panel ───────────────────────────────────────────────────
    "shop_lbl_name": {
        "EN": "Shop Name",
        "DE": "Shop-Name",
        "AR": "اسم المتجر",
    },
    "shop_lbl_logo": {
        "EN": "Logo",
        "DE": "Logo",
        "AR": "الشعار",
    },
    "shop_lbl_browse": {
        "EN": "Browse…",
        "DE": "Durchsuchen…",
        "AR": "استعراض…",
    },
    "shop_lbl_currency": {
        "EN": "Currency Symbol",
        "DE": "Währungssymbol",
        "AR": "رمز العملة",
    },
    "shop_lbl_cur_pos": {
        "EN": "Currency Position",
        "DE": "Währungsposition",
        "AR": "موضع العملة",
    },
    "shop_cur_prefix": {
        "EN": "Prefix  (€100)",
        "DE": "Präfix  (€100)",
        "AR": "بادئة  (€100)",
    },
    "shop_cur_suffix": {
        "EN": "Suffix  (100 €)",
        "DE": "Suffix  (100 €)",
        "AR": "لاحقة  (100 €)",
    },
    "shop_lbl_language": {
        "EN": "Default Language",
        "DE": "Standardsprache",
        "AR": "اللغة الافتراضية",
    },
    "shop_lbl_theme": {
        "EN": "Theme",
        "DE": "Darstellung",
        "AR": "المظهر",
    },
    "shop_theme_dark": {
        "EN": "Dark",
        "DE": "Dunkel",
        "AR": "داكن",
    },
    "shop_theme_light": {
        "EN": "Light",
        "DE": "Hell",
        "AR": "فاتح",
    },
    "shop_theme_pro_dark": {
        "EN": "Pro Dark",
        "DE": "Pro Dunkel",
        "AR": "احترافي داكن",
    },
    "shop_theme_pro_light": {
        "EN": "Pro Light",
        "DE": "Pro Hell",
        "AR": "احترافي فاتح",
    },
    "shop_lbl_pin": {
        "EN": "Admin PIN  (empty = disabled)",
        "DE": "Admin-PIN  (leer = deaktiviert)",
        "AR": "رمز المدير  (فارغ = معطل)",
    },
    "shop_lbl_contact": {
        "EN": "Contact Info",
        "DE": "Kontaktinformationen",
        "AR": "معلومات التواصل",
    },
    "shop_btn_save": {
        "EN": "Save Settings",
        "DE": "Einstellungen speichern",
        "AR": "حفظ الإعدادات",
    },
    "shop_saved": {
        "EN": "Settings saved.",
        "DE": "Einstellungen gespeichert.",
        "AR": "تم حفظ الإعدادات.",
    },
    # ── Auto-Backup settings ──────────────────────────────────────────────────
    "shop_card_backup":         {"EN": "Auto-Backup",                       "DE": "Automatisches Backup",                    "AR": "النسخ الاحتياطي التلقائي"},
    "shop_card_backup_desc":    {"EN": "Automatically back up the database on a schedule", "DE": "Datenbank automatisch sichern", "AR": "نسخ احتياطي تلقائي للقاعدة بيانات"},
    "shop_lbl_backup_enabled":  {"EN": "Enable Auto-Backup",                "DE": "Automatisches Backup aktivieren",         "AR": "تفعيل النسخ الاحتياطي التلقائي"},
    "shop_lbl_backup_interval": {"EN": "Interval (hours)",                  "DE": "Intervall (Stunden)",                     "AR": "الفاصل الزمني (ساعات)"},
    "shop_lbl_backup_retain":   {"EN": "Keep last N backups",               "DE": "Letzte N Backups behalten",               "AR": "الاحتفاظ بآخر N نسخة"},
    "shop_lbl_backup_dir":      {"EN": "Backup folder (empty = default)",   "DE": "Backup-Ordner (leer = Standard)",         "AR": "مجلد النسخ الاحتياطي (فارغ = افتراضي)"},
    "shop_backup_now":          {"EN": "Back Up Now",                       "DE": "Jetzt sichern",                           "AR": "نسخ احتياطي الآن"},
    "shop_backup_done":         {"EN": "✓ Backup created",                  "DE": "✓ Backup erstellt",                       "AR": "✓ تم إنشاء النسخة الاحتياطية"},
    "shop_backup_fail":         {"EN": "Backup failed",                     "DE": "Backup fehlgeschlagen",                   "AR": "فشل النسخ الاحتياطي"},
    "shop_backup_last":         {"EN": "Last backup: {ts}",                 "DE": "Letztes Backup: {ts}",                    "AR": "آخر نسخة احتياطية: {ts}"},
    "shop_backup_never":        {"EN": "No backups yet",                    "DE": "Noch keine Backups",                      "AR": "لا توجد نسخ احتياطية بعد"},
    # ── Categories panel ──────────────────────────────────────────────────────
    "cat_btn_add": {
        "EN": "＋  Add Category",
        "DE": "＋  Kategorie hinzufügen",
        "AR": "＋  إضافة فئة",
    },
    "cat_btn_delete": {
        "EN": "Delete",
        "DE": "Löschen",
        "AR": "حذف",
    },
    "cat_btn_move_up": {
        "EN": "↑  Up",
        "DE": "↑  Hoch",
        "AR": "↑  أعلى",
    },
    "cat_btn_move_down": {
        "EN": "↓  Down",
        "DE": "↓  Runter",
        "AR": "↓  أسفل",
    },
    "cat_lbl_name_en": {
        "EN": "Name (EN)",
        "DE": "Name (EN)",
        "AR": "الاسم (EN)",
    },
    "cat_lbl_name_de": {
        "EN": "Name (DE)",
        "DE": "Name (DE)",
        "AR": "الاسم (DE)",
    },
    "cat_lbl_name_ar": {
        "EN": "Name (AR)",
        "DE": "Name (AR)",
        "AR": "الاسم (AR)",
    },
    "cat_lbl_icon": {
        "EN": "Icon",
        "DE": "Symbol",
        "AR": "أيقونة",
    },
    "cat_lbl_active": {
        "EN": "Active (shown as tab)",
        "DE": "Aktiv (als Tab anzeigen)",
        "AR": "نشط (عرض كتبويب)",
    },
    "cat_delete_blocked": {
        "EN": "Cannot delete: category has stock entries with stock > 0.",
        "DE": "Nicht löschbar: Kategorie hat Lagereinträge mit Bestand > 0.",
        "AR": "لا يمكن الحذف: للفئة قيود مخزون بكمية > 0.",
    },
    "cat_delete_confirm": {
        "EN": "Delete category '{name}' and all its part types? This cannot be undone.",
        "DE": "Kategorie '{name}' und alle Teiletypen löschen? Nicht rückgängig zu machen.",
        "AR": "حذف الفئة '{name}' وجميع أنواع قطعها؟ لا يمكن التراجع.",
    },
    "cat_btn_save": {
        "EN": "Save Category",
        "DE": "Kategorie speichern",
        "AR": "حفظ الفئة",
    },
    "cat_no_selection": {
        "EN": "Select a category to edit.",
        "DE": "Wählen Sie eine Kategorie zum Bearbeiten.",
        "AR": "اختر فئة للتعديل.",
    },
    # ── Part types panel ──────────────────────────────────────────────────────
    "pt_lbl_category": {
        "EN": "Category:",
        "DE": "Kategorie:",
        "AR": "الفئة:",
    },
    "pt_col_key": {
        "EN": "Key",
        "DE": "Schlüssel",
        "AR": "المفتاح",
    },
    "pt_col_name": {
        "EN": "Name",
        "DE": "Name",
        "AR": "الاسم",
    },
    "pt_col_color": {
        "EN": "Color",
        "DE": "Farbe",
        "AR": "اللون",
    },
    "pt_btn_add": {
        "EN": "+ Add Part Type",
        "DE": "+ Teiletyp hinzufügen",
        "AR": "+ إضافة نوع",
    },
    "pt_btn_edit": {
        "EN": "Edit",
        "DE": "Bearbeiten",
        "AR": "تعديل",
    },
    "pt_btn_delete": {
        "EN": "Delete",
        "DE": "Löschen",
        "AR": "حذف",
    },
    "pt_lbl_key": {
        "EN": "Key  (A-Z, 0-9, _ only)",
        "DE": "Schlüssel  (A-Z, 0-9, _)",
        "AR": "المفتاح  (A-Z, 0-9, _)",
    },
    "pt_lbl_name": {
        "EN": "Display Name",
        "DE": "Anzeigename",
        "AR": "اسم العرض",
    },
    "pt_lbl_color": {
        "EN": "Accent Color",
        "DE": "Akzentfarbe",
        "AR": "لون التمييز",
    },
    "pt_delete_blocked": {
        "EN": "Cannot delete: part type has stock entries with stock > 0.",
        "DE": "Nicht löschbar: Teiletyp hat Einträge mit Bestand > 0.",
        "AR": "لا يمكن الحذف: لنوع القطعة قيود مخزون بكمية > 0.",
    },
    "pt_key_exists": {
        "EN": "Key '{key}' already exists in this category.",
        "DE": "Schlüssel '{key}' existiert bereits in dieser Kategorie.",
        "AR": "المفتاح '{key}' موجود بالفعل في هذه الفئة.",
    },
    "pt_no_selection": {
        "EN": "Select a part type to edit.",
        "DE": "Wählen Sie einen Teiletyp zum Bearbeiten.",
        "AR": "اختر نوع قطعة للتعديل.",
    },
    # ── Models panel ──────────────────────────────────────────────────────────
    "mdl_btn_add": {
        "EN": "＋  Add Model",
        "DE": "＋  Modell hinzufügen",
        "AR": "＋  إضافة طراز",
    },
    "mdl_btn_delete": {
        "EN": "Delete Selected",
        "DE": "Auswahl löschen",
        "AR": "حذف المحدد",
    },
    "mdl_btn_rename": {
        "EN": "Rename",
        "DE": "Umbenennen",
        "AR": "إعادة تسمية",
    },
    "mdl_delete_confirm": {
        "EN": "Delete {n} model(s)? Stock history will also be deleted.",
        "DE": "{n} Modell(e) löschen? Lagerhistorie wird ebenfalls gelöscht.",
        "AR": "حذف {n} طراز؟ سيُحذف سجل المخزون أيضاً.",
    },
    "mdl_delete_blocked": {
        "EN": "Cannot delete: some selected models have stock > 0.",
        "DE": "Nicht löschbar: Einige Modelle haben Bestand > 0.",
        "AR": "لا يمكن الحذف: بعض الطرازات لها مخزون > 0.",
    },
    "mdl_rename_title": {
        "EN": "Rename Model",
        "DE": "Modell umbenennen",
        "AR": "إعادة تسمية الطراز",
    },
    "mdl_rename_lbl": {
        "EN": "New name:",
        "DE": "Neuer Name:",
        "AR": "الاسم الجديد:",
    },
    "mdl_col_brand": {
        "EN": "Brand",
        "DE": "Marke",
        "AR": "العلامة",
    },
    "mdl_col_model": {
        "EN": "Model",
        "DE": "Modell",
        "AR": "الطراز",
    },
    # ── PIN gate ──────────────────────────────────────────────────────────────
    "pin_title": {
        "EN": "Admin Access",
        "DE": "Admin-Zugang",
        "AR": "وصول المدير",
    },
    "pin_prompt": {
        "EN": "Enter Admin PIN:",
        "DE": "Admin-PIN eingeben:",
        "AR": "أدخل رمز المدير:",
    },
    "pin_wrong": {
        "EN": "Incorrect PIN.",
        "DE": "Falscher PIN.",
        "AR": "الرمز غير صحيح.",
    },
    "tooltip_admin": {
        "EN": "Admin Settings  (Ctrl+Alt+A)",
        "DE": "Admin-Einstellungen  (Ctrl+Alt+A)",
        "AR": "إعدادات الإدارة  (Ctrl+Alt+A)",
    },
    "tooltip_stock_in": {
        "EN": "Stock In  (Ctrl+I)",
        "DE": "Wareneingang  (Ctrl+I)",
        "AR": "إضافة مخزون  (Ctrl+I)",
    },
    "tooltip_stock_out": {
        "EN": "Stock Out  (Ctrl+O)",
        "DE": "Warenausgang  (Ctrl+O)",
        "AR": "سحب مخزون  (Ctrl+O)",
    },
    "tooltip_adjust": {
        "EN": "Adjust Stock  (Ctrl+J)",
        "DE": "Bestand anpassen  (Ctrl+J)",
        "AR": "ضبط المخزون  (Ctrl+J)",
    },
    "tooltip_new_product": {
        "EN": "New Product  (Ctrl+N)",
        "DE": "Neues Produkt  (Ctrl+N)",
        "AR": "منتج جديد  (Ctrl+N)",
    },
    "tooltip_export_csv": {
        "EN": "Export CSV  (Ctrl+P)",
        "DE": "CSV exportieren  (Ctrl+P)",
        "AR": "تصدير CSV  (Ctrl+P)",
    },
    # ── Phase 4: Analytics ──────────────────────────────────────────────────
    "nav_analytics": {
        "EN": "Analytics",
        "DE": "Analysen",
        "AR": "التحليلات",
    },
    "analytics_title": {
        "EN": "Analytics Dashboard",
        "DE": "Analyse-Dashboard",
        "AR": "لوحة التحليلات",
    },
    "analytics_stock_health": {
        "EN": "Stock Health Overview",
        "DE": "Bestandsgesundheit",
        "AR": "نظرة عامة على صحة المخزون",
    },
    "analytics_by_category": {
        "EN": "Units by Category",
        "DE": "Einheiten nach Kategorie",
        "AR": "الوحدات حسب الفئة",
    },
    "analytics_activity_trend": {
        "EN": "Transaction Activity (Last 30 Days)",
        "DE": "Transaktionsaktivität (Letzte 30 Tage)",
        "AR": "نشاط المعاملات (آخر 30 يوم)",
    },
    "analytics_top_low_stock": {
        "EN": "Top Low-Stock Items",
        "DE": "Artikel mit niedrigem Bestand",
        "AR": "أهم العناصر منخفضة المخزون",
    },
    "analytics_total": {
        "EN": "Total Items",
        "DE": "Gesamt",
        "AR": "إجمالي العناصر",
    },
    "analytics_products": {
        "EN": "Products",
        "DE": "Produkte",
        "AR": "المنتجات",
    },
    "analytics_kpi_total_items": {
        "EN": "TOTAL ITEMS",
        "DE": "GESAMTARTIKEL",
        "AR": "إجمالي العناصر",
    },
    "analytics_kpi_total_units": {
        "EN": "TOTAL UNITS",
        "DE": "GESAMTEINHEITEN",
        "AR": "إجمالي الوحدات",
    },
    "analytics_kpi_inventory_value": {
        "EN": "INVENTORY VALUE",
        "DE": "BESTANDSWERT",
        "AR": "قيمة المخزون",
    },
    "analytics_kpi_stock_health": {
        "EN": "STOCK HEALTH",
        "DE": "BESTANDSGESUNDHEIT",
        "AR": "صحة المخزون",
    },
    "analytics_kpi_products_matrix": {
        "EN": "Products + matrix entries",
        "DE": "Produkte + Matrix-Einträge",
        "AR": "منتجات + إدخالات المصفوفة",
    },
    "analytics_kpi_across_items": {
        "EN": "Across {n} items",
        "DE": "Über {n} Artikel",
        "AR": "عبر {n} عنصر",
    },
    "analytics_kpi_at_sell_price": {
        "EN": "At sell price",
        "DE": "Zum Verkaufspreis",
        "AR": "بسعر البيع",
    },
    "analytics_kpi_items_ok": {
        "EN": "{n} items in good standing",
        "DE": "{n} Artikel in gutem Zustand",
        "AR": "{n} عنصر بحالة جيدة",
    },
    # ── Phase 4: Bulk Operations ─────────────────────────────────────────────
    "ctx_bulk_price": {
        "EN": "Bulk Update Price…",
        "DE": "Preis-Massenupdate…",
        "AR": "تحديث الأسعار بالجملة…",
    },
    "bulk_price_title": {
        "EN": "Bulk Price Update",
        "DE": "Preis-Massenupdate",
        "AR": "تحديث الأسعار بالجملة",
    },
    "bulk_price_mode": {
        "EN": "Price Update Mode",
        "DE": "Preis-Aktualisierungsmodus",
        "AR": "وضع تحديث السعر",
    },
    "bulk_price_set": {
        "EN": "Set exact price",
        "DE": "Exakten Preis festlegen",
        "AR": "تعيين سعر محدد",
    },
    "bulk_price_increase_pct": {
        "EN": "Increase by %",
        "DE": "Erhöhen um %",
        "AR": "زيادة بنسبة %",
    },
    "bulk_price_decrease_pct": {
        "EN": "Decrease by %",
        "DE": "Reduzieren um %",
        "AR": "تخفيض بنسبة %",
    },
    "bulk_price_value": {
        "EN": "Value",
        "DE": "Wert",
        "AR": "القيمة",
    },
    "bulk_price_confirm": {
        "EN": "Update price for {n} items?",
        "DE": "Preis für {n} Artikel aktualisieren?",
        "AR": "تحديث سعر {n} عنصر؟",
    },
    "bulk_price_done": {
        "EN": "Updated prices for {n} items",
        "DE": "Preise für {n} Artikel aktualisiert",
        "AR": "تم تحديث أسعار {n} عنصر",
    },
    # ── Phase 4: Excel Export ─────────────────────────────────────────────────
    "export_excel": {
        "EN": "Export Excel (.xlsx)",
        "DE": "Excel exportieren (.xlsx)",
        "AR": "تصدير Excel (.xlsx)",
    },
    "export_excel_success": {
        "EN": "Excel exported to {path}",
        "DE": "Excel exportiert nach {path}",
        "AR": "تم تصدير Excel إلى {path}",
    },
    "export_excel_failed": {
        "EN": "Excel export failed",
        "DE": "Excel-Export fehlgeschlagen",
        "AR": "فشل تصدير Excel",
    },
    # ── Setup wizard ─────────────────────────────────────────────────────────
    "wizard_welcome_title": {
        "EN": "Welcome to Stock Manager Pro",
        "DE": "Willkommen bei Stock Manager Pro",
        "AR": "مرحباً بـ Stock Manager Pro",
    },
    "wizard_welcome_sub": {
        "EN": "Let's configure your shop in 2 quick steps.",
        "DE": "Richten Sie Ihren Shop in 2 Schritten ein.",
        "AR": "لنقم بإعداد متجرك في خطوتين.",
    },
    "wizard_btn_start": {
        "EN": "Get Started  →",
        "DE": "Los geht's  →",
        "AR": "ابدأ  →",
    },
    "wizard_shop_title": {
        "EN": "Your Shop",
        "DE": "Ihr Shop",
        "AR": "متجرك",
    },
    "wizard_data_title": {
        "EN": "Starting Data",
        "DE": "Startdaten",
        "AR": "البيانات الأولية",
    },
    "wizard_opt_fresh": {
        "EN": "Start fresh — I'll add my own categories and models",
        "DE": "Ohne Vordaten starten — eigene Kategorien hinzufügen",
        "AR": "بدء جديد — سأضيف فئاتي وطرازاتي",
    },
    "wizard_opt_demo": {
        "EN": "Load phone shop demo data  (Apple / Samsung models, 6 categories)",
        "DE": "Handy-Shop Demo laden  (Apple / Samsung, 6 Kategorien)",
        "AR": "تحميل بيانات تجريبية لمتجر هواتف  (Apple / Samsung، 6 فئات)",
    },
    "wizard_btn_finish": {
        "EN": "Finish Setup",
        "DE": "Einrichtung abschließen",
        "AR": "إنهاء الإعداد",
    },
    "wizard_btn_back": {
        "EN": "←  Back",
        "DE": "←  Zurück",
        "AR": "←  رجوع",
    },
    # ── Demo data loading ─────────────────────────────────────────────────────
    "demo_load_title": {
        "EN": "Load Demo Data",
        "DE": "Demo-Daten laden",
        "AR": "تحميل بيانات تجريبية",
    },
    "demo_load_body": {
        "EN": "Add Galaxy@Phone demo data (42 Apple/Samsung models, 6 categories)?\nExisting data is preserved.",
        "DE": "Galaxy@Phone Demo-Daten hinzufügen (42 Apple/Samsung-Modelle, 6 Kategorien)?\nBestehende Daten bleiben erhalten.",
        "AR": "إضافة بيانات Galaxy@Phone التجريبية (42 طراز، 6 فئات)؟\nالبيانات الموجودة ستبقى.",
    },
    "demo_loaded": {
        "EN": "Demo data loaded.",
        "DE": "Demo-Daten geladen.",
        "AR": "تم تحميل البيانات التجريبية.",
    },
    # ── Matrix column headers ─────────────────────────────────────────────────
    "col_stamm_zahl": {
        "EN": "Min-Stock",
        "DE": "Stamm-Zahl",
        "AR": "الحد الأدنى",
    },
    "col_best_bung": {
        "EN": "Δ Difference",
        "DE": "Best-Bung",
        "AR": "الفرق",
    },
    "col_inventur": {
        "EN": "Order",
        "DE": "Bestellung",
        "AR": "الطلب",
    },
    # ── ThresholdDialog form label ────────────────────────────────────────────
    "lbl_stamm_zahl": {
        "EN": "Min-Stock:",
        "DE": "Stamm-Zahl:",
        "AR": "الحد الأدنى:",
    },
    # ── Sidebar navigation ──────────────────────────────────────────────────
    "nav_inventory": {
        "EN": "Inventory",
        "DE": "Inventar",
        "AR": "المخزون",
    },
    "nav_transactions": {
        "EN": "Transactions",
        "DE": "Transaktionen",
        "AR": "المعاملات",
    },
    "nav_suppliers": {
        "EN": "Suppliers",
        "DE": "Lieferanten",
        "AR": "الموردون",
    },
    "nav_audit": {
        "EN": "Audit",
        "DE": "Inventur",
        "AR": "جرد المخزون",
    },
    "nav_price_lists": {
        "EN": "Price Lists",
        "DE": "Preislisten",
        "AR": "قوائم الأسعار",
    },
    "nav_quick_scan": {
        "EN": "Quick Scan",
        "DE": "Schnellscan",
        "AR": "مسح سريع",
    },
    # ── Suppliers Management ───────────────────────────────────────────────────
    "sup_title": {
        "EN": "Suppliers",
        "DE": "Lieferanten",
        "AR": "الموردون",
    },
    "sup_subtitle": {
        "EN": "Manage your suppliers and contacts",
        "DE": "Verwalten Sie Ihre Lieferanten und Kontakte",
        "AR": "إدارة الموردين والجهات الاتصال",
    },
    "sup_btn_add": {
        "EN": "Add Supplier",
        "DE": "Lieferant hinzufügen",
        "AR": "إضافة مورد",
    },
    "sup_search_ph": {
        "EN": "Search suppliers by name, email, or phone…",
        "DE": "Nach Lieferanten suchen…",
        "AR": "البحث عن الموردين…",
    },
    "sup_col_name": {
        "EN": "Name",
        "DE": "Name",
        "AR": "الاسم",
    },
    "sup_col_contact": {
        "EN": "Contact",
        "DE": "Ansprechpartner",
        "AR": "جهة الاتصال",
    },
    "sup_col_phone": {
        "EN": "Phone",
        "DE": "Telefon",
        "AR": "الهاتف",
    },
    "sup_col_email": {
        "EN": "Email",
        "DE": "E-Mail",
        "AR": "البريد الإلكتروني",
    },
    "sup_col_items": {
        "EN": "Items",
        "DE": "Artikel",
        "AR": "المنتجات",
    },
    "sup_col_rating": {
        "EN": "Rating",
        "DE": "Bewertung",
        "AR": "التقييم",
    },
    "sup_col_actions": {
        "EN": "Actions",
        "DE": "Aktionen",
        "AR": "الإجراءات",
    },
    "sup_status_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشط",
    },
    "sup_status_inactive": {
        "EN": "Inactive",
        "DE": "Inaktiv",
        "AR": "غير نشط",
    },
    "sup_empty_title": {
        "EN": "No Suppliers Yet",
        "DE": "Noch keine Lieferanten",
        "AR": "لا توجد موردون بعد",
    },
    "sup_empty_sub": {
        "EN": "Create your first supplier to get started",
        "DE": "Erstellen Sie Ihren ersten Lieferanten",
        "AR": "أنشئ مورد أول لتبدأ",
    },
    "sup_dlg_title": {
        "EN": "Add Supplier",
        "DE": "Lieferant hinzufügen",
        "AR": "إضافة مورد",
    },
    "sup_dlg_edit_title": {
        "EN": "Edit Supplier",
        "DE": "Lieferant bearbeiten",
        "AR": "تحرير المورد",
    },
    "sup_dlg_name": {
        "EN": "Company Name",
        "DE": "Unternehmensname",
        "AR": "اسم الشركة",
    },
    "sup_dlg_contact": {
        "EN": "Contact Person",
        "DE": "Ansprechpartner",
        "AR": "جهة الاتصال",
    },
    "sup_dlg_phone": {
        "EN": "Phone",
        "DE": "Telefon",
        "AR": "الهاتف",
    },
    "sup_dlg_email": {
        "EN": "Email",
        "DE": "E-Mail",
        "AR": "البريد الإلكتروني",
    },
    "sup_dlg_address": {
        "EN": "Address",
        "DE": "Adresse",
        "AR": "العنوان",
    },
    "sup_dlg_notes": {
        "EN": "Notes",
        "DE": "Notizen",
        "AR": "ملاحظات",
    },
    "sup_dlg_rating": {
        "EN": "Rating (0-5)",
        "DE": "Bewertung (0-5)",
        "AR": "التقييم (0-5)",
    },
    "sup_items_title": {
        "EN": "Manage Items",
        "DE": "Artikel verwalten",
        "AR": "إدارة المنتجات",
    },
    "sup_items_link": {
        "EN": "Link Item",
        "DE": "Artikel verknüpfen",
        "AR": "ربط المنتج",
    },
    "sup_items_cost": {
        "EN": "Cost",
        "DE": "Kosten",
        "AR": "التكلفة",
    },
    "sup_items_lead": {
        "EN": "Lead Time",
        "DE": "Lieferzeit",
        "AR": "وقت التسليم",
    },
    "sup_items_sku": {
        "EN": "SKU",
        "DE": "Artikelnummer",
        "AR": "رقم SKU",
    },
    "sup_kpi_total": {
        "EN": "Total Suppliers",
        "DE": "Gesamtlieferanten",
        "AR": "إجمالي الموردين",
    },
    "sup_kpi_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشط",
    },
    "sup_kpi_inactive": {
        "EN": "Inactive",
        "DE": "Inaktiv",
        "AR": "غير نشط",
    },
    "sup_kpi_avg_rating": {
        "EN": "Avg Rating",
        "DE": "Durchschnittsbewertung",
        "AR": "متوسط التقييم",
    },
    "sup_warn_name": {
        "EN": "Supplier name is required",
        "DE": "Der Name des Lieferanten ist erforderlich",
        "AR": "اسم المورد مطلوب",
    },
    "sup_warn_search": {
        "EN": "Enter at least 2 characters to search",
        "DE": "Geben Sie mindestens 2 Zeichen ein",
        "AR": "أدخل حرفين على الأقل للبحث",
    },
    "sup_dlg_item_search": {
        "EN": "Search items…",
        "DE": "Nach Artikeln suchen…",
        "AR": "البحث عن المنتجات…",
    },
    # ── Quick Scan tab ────────────────────────────────────────────────────────
    "qscan_title":        {"EN": "Quick Scan",                    "DE": "Schnellscan",                   "AR": "مسح سريع"},
    "qscan_hint":         {"EN": "Scan a command barcode to begin a session", "DE": "Scannen Sie einen Befehlsbarcode", "AR": "امسح باركود الأمر لبدء جلسة"},
    "qscan_scan_field":   {"EN": "Scan barcode here…",            "DE": "Barcode hier scannen…",          "AR": "امسح الباركود هنا…"},
    "qscan_mode_idle":    {"EN": "Scan a command barcode to begin","DE": "Befehlsbarcode scannen",         "AR": "امسح باركود الأمر للبدء"},
    "qscan_mode_takeout": {"EN": "TAKEOUT MODE — Scan items to remove from stock", "DE": "AUSGABE — Artikel scannen zum Ausbuchen", "AR": "وضع السحب — امسح المنتجات لإزالتها"},
    "qscan_mode_insert":  {"EN": "INSERT MODE — Scan items to add to stock",      "DE": "EINGANG — Artikel scannen zum Einbuchen",  "AR": "وضع الإضافة — امسح المنتجات لإضافتها"},
    "qscan_pending_hdr":  {"EN": "PENDING ({n} items)",            "DE": "AUSSTEHEND ({n} Artikel)",       "AR": "قيد الانتظار ({n} منتج)"},
    "qscan_pending_empty": {"EN": "No items scanned yet",          "DE": "Noch keine Artikel gescannt",    "AR": "لم يتم مسح أي منتج بعد"},
    "qscan_total_summary": {"EN": "Total: {ops} units on {items} items", "DE": "Gesamt: {ops} Einheiten für {items} Artikel", "AR": "الإجمالي: {ops} وحدة على {items} منتج"},
    "qscan_confirm_btn":  {"EN": "Confirm All",                   "DE": "Alle bestätigen",                "AR": "تأكيد الكل"},
    "qscan_cancel_btn":   {"EN": "Cancel Session",                "DE": "Sitzung abbrechen",              "AR": "إلغاء الجلسة"},
    "qscan_cancel_confirm": {"EN": "Cancel current session? All pending items will be discarded.", "DE": "Sitzung abbrechen? Alle ausstehenden Artikel werden verworfen.", "AR": "إلغاء الجلسة الحالية؟ سيتم تجاهل جميع المنتجات المعلقة."},
    "qscan_committed":    {"EN": "✓  Committed {n} operations",   "DE": "✓  {n} Vorgänge bestätigt",      "AR": "✓  تم تنفيذ {n} عملية"},
    "qscan_commit_partial": {"EN": "⚠  {ok} succeeded, {fail} failed", "DE": "⚠  {ok} erfolgreich, {fail} fehlgeschlagen", "AR": "⚠  {ok} نجحت، {fail} فشلت"},
    "qscan_item_added":   {"EN": "Added: {name} (qty: {qty})",    "DE": "Hinzugefügt: {name} (Menge: {qty})", "AR": "أضيف: {name} (الكمية: {qty})"},
    "qscan_item_incremented": {"EN": "{name} qty → {qty}",        "DE": "{name} Menge → {qty}",           "AR": "{name} الكمية → {qty}"},
    "qscan_no_mode":      {"EN": "Scan a TAKEOUT or INSERT command first", "DE": "Zuerst Befehlsbarcode scannen", "AR": "امسح باركود الأمر أولاً"},
    "qscan_scan_color":   {"EN": "Scan color barcode for: {name}\nAvailable: {colors}", "DE": "Farb-Barcode scannen fuer: {name}\nVerfuegbar: {colors}", "AR": "امسح باركود اللون لـ: {name}\nالمتاح: {colors}"},
    "qscan_color_not_found": {"EN": "Color '{color}' not available for this item", "DE": "Farbe '{color}' nicht verfuegbar", "AR": "اللون '{color}' غير متاح لهذا المنتج"},
    "qscan_waiting_color": {"EN": "Scan COLOR barcode", "DE": "FARB-Barcode scannen", "AR": "امسح باركود اللون"},
    "qscan_session_active": {"EN": "A {mode} session is active. Confirm or cancel first.", "DE": "Eine {mode}-Sitzung ist aktiv. Zuerst bestätigen oder abbrechen.", "AR": "جلسة {mode} نشطة. قم بالتأكيد أو الإلغاء أولاً."},
    "qscan_not_found":    {"EN": "✕  Barcode not found: {bc}",    "DE": "✕  Barcode nicht gefunden: {bc}", "AR": "✕  الباركود غير موجود: {bc}"},
    "qscan_out_of_stock": {"EN": "⚠  Out of stock: {name}",       "DE": "⚠  Ausverkauft: {name}",          "AR": "⚠  نفد المخزون: {name}"},
    "qscan_recent":       {"EN": "RECENT SESSIONS",               "DE": "LETZTE SITZUNGEN",               "AR": "الجلسات الأخيرة"},
    "qscan_nav_mode":     {"EN": "Entered {mode} mode",                    "DE": "{mode}-Modus gestartet",              "AR": "تم الدخول في وضع {mode}"},
    "qscan_settings_btn": {"EN": "Scan Settings",                 "DE": "Scan-Einstellungen",             "AR": "إعدادات المسح"},
    # ── Barcode assignment ────────────────────────────────────────────────────
    "barcode_assign_title":  {"EN": "Assign Barcode",              "DE": "Barcode zuweisen",               "AR": "تعيين الباركود"},
    "barcode_current":       {"EN": "Current Barcode:",            "DE": "Aktueller Barcode:",             "AR": "الباركود الحالي:"},
    "barcode_new":           {"EN": "New Barcode:",                "DE": "Neuer Barcode:",                 "AR": "الباركود الجديد:"},
    "barcode_none":          {"EN": "No barcode assigned",         "DE": "Kein Barcode zugewiesen",        "AR": "لا يوجد باركود"},
    "barcode_saved":         {"EN": "Barcode saved",               "DE": "Barcode gespeichert",            "AR": "تم حفظ الباركود"},
    "barcode_duplicate":     {"EN": "This barcode is already assigned to another item", "DE": "Dieser Barcode ist bereits vergeben", "AR": "هذا الباركود مخصص بالفعل لمنتج آخر"},
    "barcode_ctx_assign":    {"EN": "Assign Barcode…",             "DE": "Barcode zuweisen…",              "AR": "تعيين الباركود…"},
    # ── Admin scan settings ───────────────────────────────────────────────────
    "admin_tab_scan":     {"EN": "Scan Settings",                  "DE": "Scan-Einstellungen",             "AR": "إعدادات المسح"},
    "scan_cfg_header":    {"EN": "Command Barcodes",               "DE": "Befehlsbarcodes",                "AR": "باركودات الأوامر"},
    "scan_cfg_takeout":   {"EN": "Takeout Command:",               "DE": "Ausgabe-Befehl:",                "AR": "أمر السحب:"},
    "scan_cfg_insert":    {"EN": "Insert Command:",                "DE": "Eingang-Befehl:",                "AR": "أمر الإضافة:"},
    "scan_cfg_confirm":   {"EN": "Confirm Command:",               "DE": "Bestätigungs-Befehl:",           "AR": "أمر التأكيد:"},
    "scan_cfg_hint":      {"EN": "Print these barcodes and keep them at your workstation", "DE": "Drucken Sie diese Barcodes und bewahren Sie sie am Arbeitsplatz auf", "AR": "اطبع هذه الباركودات واحتفظ بها في مكان عملك"},
    "scan_cfg_saved":     {"EN": "Scan settings saved",            "DE": "Scan-Einstellungen gespeichert", "AR": "تم حفظ إعدادات المسح"},
    # ── Stock Operations tab ──────────────────────────────────────────────────
    "stockops_title": {
        "EN": "Stock Operations",
        "DE": "Lagervorgänge",
        "AR": "عمليات المخزون",
    },
    "stockops_search": {
        "EN": "Search product or scan barcode…",
        "DE": "Produkt suchen oder Barcode scannen…",
        "AR": "ابحث عن منتج أو امسح الباركود…",
    },
    "stockops_select_prompt": {
        "EN": "Select a product from the list to perform stock operations",
        "DE": "Wählen Sie ein Produkt für Lagervorgänge",
        "AR": "اختر منتجاً من القائمة لإجراء عمليات المخزون",
    },
    "stockops_selected": {
        "EN": "Selected: {name}",
        "DE": "Ausgewählt: {name}",
        "AR": "المحدد: {name}",
    },
    "stockops_qty_label": {
        "EN": "Quantity:",
        "DE": "Menge:",
        "AR": "الكمية:",
    },
    "stockops_note_label": {
        "EN": "Note (optional):",
        "DE": "Notiz (optional):",
        "AR": "ملاحظة (اختياري):",
    },
    # ── Stock Ops KPI & redesign ─────────────────────────────────────────────
    "stockops_kpi_total": {
        "EN": "TOTAL ITEMS",
        "DE": "GESAMT",
        "AR": "إجمالي المنتجات",
    },
    "stockops_kpi_units": {
        "EN": "TOTAL UNITS",
        "DE": "GESAMTEINHEITEN",
        "AR": "إجمالي الوحدات",
    },
    "stockops_kpi_low": {
        "EN": "LOW STOCK",
        "DE": "NIEDRIGER BESTAND",
        "AR": "مخزون منخفض",
    },
    "stockops_kpi_out": {
        "EN": "OUT OF STOCK",
        "DE": "NICHT VORRÄTIG",
        "AR": "نفد المخزون",
    },
    "stockops_kpi_value": {
        "EN": "INVENTORY VALUE",
        "DE": "BESTANDSWERT",
        "AR": "قيمة المخزون",
    },
    "stockops_filter_all": {
        "EN": "All Items",
        "DE": "Alle Artikel",
        "AR": "كل المنتجات",
    },
    "stockops_filter_low": {
        "EN": "Low Stock",
        "DE": "Niedriger Bestand",
        "AR": "مخزون منخفض",
    },
    "stockops_filter_out": {
        "EN": "Out of Stock",
        "DE": "Nicht vorrätig",
        "AR": "نفد المخزون",
    },
    "stockops_filter_products": {
        "EN": "Products Only",
        "DE": "Nur Produkte",
        "AR": "المنتجات فقط",
    },
    "stockops_subtitle": {
        "EN": "Manage stock levels, perform operations, and track inventory movements",
        "DE": "Bestandsmengen verwalten, Vorgänge durchführen und Bestandsbewegungen verfolgen",
        "AR": "إدارة مستويات المخزون وتنفيذ العمليات وتتبع حركة المخزون",
    },
    "stockops_col_product": {
        "EN": "Product",
        "DE": "Produkt",
        "AR": "المنتج",
    },
    "stockops_col_barcode": {
        "EN": "Barcode",
        "DE": "Barcode",
        "AR": "الباركود",
    },
    "stockops_col_stock": {
        "EN": "Stock",
        "DE": "Bestand",
        "AR": "المخزون",
    },
    "stockops_col_min": {
        "EN": "Min",
        "DE": "Min",
        "AR": "الحد الأدنى",
    },
    "stockops_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "stockops_col_actions": {
        "EN": "Quick Actions",
        "DE": "Schnellaktionen",
        "AR": "إجراءات سريعة",
    },
    "stockops_empty_title": {
        "EN": "No items found",
        "DE": "Keine Artikel gefunden",
        "AR": "لم يتم العثور على منتجات",
    },
    "stockops_empty_sub": {
        "EN": "Try adjusting your search or filter criteria",
        "DE": "Versuchen Sie, Ihre Such- oder Filterkriterien anzupassen",
        "AR": "حاول تعديل معايير البحث أو التصفية",
    },
    "stockops_op_success": {
        "EN": "{op} successful: {before} → {after}",
        "DE": "{op} erfolgreich: {before} → {after}",
        "AR": "تمت العملية {op} بنجاح: {before} ← {after}",
    },
    "stockops_detail_title": {
        "EN": "ITEM DETAILS",
        "DE": "ARTIKELDETAILS",
        "AR": "تفاصيل المنتج",
    },
    "stockops_quick_op": {
        "EN": "QUICK OPERATION",
        "DE": "SCHNELLVORGANG",
        "AR": "عملية سريعة",
    },
    "stockops_history": {
        "EN": "RECENT ACTIVITY",
        "DE": "LETZTE AKTIVITÄT",
        "AR": "النشاط الأخير",
    },
    # ── Purchase Orders ─────────────────────────────────────────────────────────
    "nav_purchase_orders": {
        "EN": "Purchase Orders",
        "DE": "Bestellungen",
        "AR": "أوامر الشراء",
    },
    "po_title": {
        "EN": "Purchase Orders",
        "DE": "Bestellungen",
        "AR": "أوامر الشراء",
    },
    "po_subtitle": {
        "EN": "Create and manage purchase orders for your suppliers",
        "DE": "Erstellen und verwalten Sie Bestellungen für Ihre Lieferanten",
        "AR": "إنشاء وإدارة أوامر الشراء للموردين",
    },
    "po_btn_new": {
        "EN": "+ New Order",
        "DE": "+ Neue Bestellung",
        "AR": "+ طلب جديد",
    },
    "po_kpi_total": {
        "EN": "TOTAL ORDERS",
        "DE": "GESAMT",
        "AR": "إجمالي الطلبات",
    },
    "po_kpi_draft": {
        "EN": "DRAFTS",
        "DE": "ENTWÜRFE",
        "AR": "مسودات",
    },
    "po_kpi_sent": {
        "EN": "SENT",
        "DE": "GESENDET",
        "AR": "مُرسلة",
    },
    "po_kpi_received": {
        "EN": "RECEIVED",
        "DE": "EMPFANGEN",
        "AR": "مُستلمة",
    },
    "po_col_number": {
        "EN": "PO Number",
        "DE": "Bestellnr.",
        "AR": "رقم الطلب",
    },
    "po_col_supplier": {
        "EN": "Supplier",
        "DE": "Lieferant",
        "AR": "المورد",
    },
    "po_col_items": {
        "EN": "Items",
        "DE": "Artikel",
        "AR": "المنتجات",
    },
    "po_col_total": {
        "EN": "Total",
        "DE": "Gesamt",
        "AR": "الإجمالي",
    },
    "po_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "po_col_date": {
        "EN": "Date",
        "DE": "Datum",
        "AR": "التاريخ",
    },
    "po_status_draft": {
        "EN": "Draft",
        "DE": "Entwurf",
        "AR": "مسودة",
    },
    "po_status_sent": {
        "EN": "Sent",
        "DE": "Gesendet",
        "AR": "مُرسل",
    },
    "po_status_partial": {
        "EN": "Partial",
        "DE": "Teilweise",
        "AR": "جزئي",
    },
    "po_status_received": {
        "EN": "Received",
        "DE": "Empfangen",
        "AR": "مُستلم",
    },
    "po_status_closed": {
        "EN": "Closed",
        "DE": "Geschlossen",
        "AR": "مغلق",
    },
    "po_status_cancelled": {
        "EN": "Cancelled",
        "DE": "Storniert",
        "AR": "ملغى",
    },
    "po_filter_all": {
        "EN": "All",
        "DE": "Alle",
        "AR": "الكل",
    },
    "po_dlg_title_new": {
        "EN": "New Purchase Order",
        "DE": "Neue Bestellung",
        "AR": "طلب شراء جديد",
    },
    "po_dlg_title_edit": {
        "EN": "Edit Purchase Order",
        "DE": "Bestellung bearbeiten",
        "AR": "تعديل طلب الشراء",
    },
    "po_dlg_supplier": {
        "EN": "Supplier:",
        "DE": "Lieferant:",
        "AR": "المورد:",
    },
    "po_dlg_notes": {
        "EN": "Notes:",
        "DE": "Notizen:",
        "AR": "ملاحظات:",
    },
    "po_dlg_add_item": {
        "EN": "+ Add Item",
        "DE": "+ Artikel hinzufügen",
        "AR": "+ إضافة منتج",
    },
    "po_dlg_item_search": {
        "EN": "Search item to add…",
        "DE": "Artikel suchen…",
        "AR": "البحث عن منتج لإضافته…",
    },
    "po_dlg_qty": {
        "EN": "Qty",
        "DE": "Menge",
        "AR": "الكمية",
    },
    "po_dlg_cost": {
        "EN": "Cost",
        "DE": "Preis",
        "AR": "التكلفة",
    },
    "po_action_send": {
        "EN": "Send to Supplier",
        "DE": "An Lieferanten senden",
        "AR": "إرسال للمورد",
    },
    "po_action_receive": {
        "EN": "Receive Items",
        "DE": "Waren empfangen",
        "AR": "استلام المنتجات",
    },
    "po_action_close": {
        "EN": "Close Order",
        "DE": "Bestellung schließen",
        "AR": "إغلاق الطلب",
    },
    "po_action_cancel": {
        "EN": "Cancel Order",
        "DE": "Bestellung stornieren",
        "AR": "إلغاء الطلب",
    },
    "po_confirm_delete": {
        "EN": "Delete this purchase order?",
        "DE": "Diese Bestellung löschen?",
        "AR": "حذف هذا الطلب؟",
    },
    "po_empty_title": {
        "EN": "No purchase orders yet",
        "DE": "Noch keine Bestellungen",
        "AR": "لا توجد أوامر شراء بعد",
    },
    "po_empty_sub": {
        "EN": "Create your first order to start tracking purchases",
        "DE": "Erstellen Sie Ihre erste Bestellung, um Einkäufe zu verfolgen",
        "AR": "أنشئ أول طلب لبدء تتبع المشتريات",
    },
    "po_receive_success": {
        "EN": "Received {units} units across {items} items",
        "DE": "{units} Einheiten für {items} Artikel empfangen",
        "AR": "تم استلام {units} وحدة عبر {items} منتج",
    },
    # ── Returns ──────────────────────────────────────────────────────────────
    "nav_returns": {
        "EN": "Returns",
        "DE": "Rückgaben",
        "AR": "المرتجعات",
    },
    "ret_title": {
        "EN": "Returns",
        "DE": "Rückgaben",
        "AR": "المرتجعات",
    },
    "ret_subtitle": {
        "EN": "Process and track product returns",
        "DE": "Produktrückgaben verarbeiten und verfolgen",
        "AR": "معالجة وتتبع مرتجعات المنتجات",
    },
    "ret_btn_new": {
        "EN": "+ New Return",
        "DE": "+ Neue Rückgabe",
        "AR": "+ مرتجع جديد",
    },
    "ret_col_item": {
        "EN": "Item",
        "DE": "Artikel",
        "AR": "المنتج",
    },
    "ret_col_qty": {
        "EN": "Quantity",
        "DE": "Menge",
        "AR": "الكمية",
    },
    "ret_col_reason": {
        "EN": "Reason",
        "DE": "Grund",
        "AR": "السبب",
    },
    "ret_col_action": {
        "EN": "Action",
        "DE": "Aktion",
        "AR": "الإجراء",
    },
    "ret_col_refund": {
        "EN": "Refund",
        "DE": "Erstattung",
        "AR": "الاسترداد",
    },
    "ret_col_date": {
        "EN": "Date",
        "DE": "Datum",
        "AR": "التاريخ",
    },
    "ret_action_restock": {
        "EN": "Restock",
        "DE": "Einlagern",
        "AR": "إعادة التخزين",
    },
    "ret_action_writeoff": {
        "EN": "Write Off",
        "DE": "Abschreiben",
        "AR": "شطب",
    },
    "ret_dlg_title": {
        "EN": "Process Return",
        "DE": "Rückgabe verarbeiten",
        "AR": "معالجة المرتجع",
    },
    "ret_dlg_item": {
        "EN": "Item:",
        "DE": "Artikel:",
        "AR": "المنتج:",
    },
    "ret_dlg_qty": {
        "EN": "Quantity:",
        "DE": "Menge:",
        "AR": "الكمية:",
    },
    "ret_dlg_reason": {
        "EN": "Reason:",
        "DE": "Grund:",
        "AR": "السبب:",
    },
    "ret_dlg_action": {
        "EN": "Action:",
        "DE": "Aktion:",
        "AR": "الإجراء:",
    },
    "ret_dlg_refund": {
        "EN": "Refund Amount:",
        "DE": "Erstattungsbetrag:",
        "AR": "مبلغ الاسترداد:",
    },
    "ret_kpi_total": {
        "EN": "TOTAL RETURNS",
        "DE": "GESAMT",
        "AR": "إجمالي المرتجعات",
    },
    "ret_kpi_restocked": {
        "EN": "RESTOCKED",
        "DE": "EINGELAGERT",
        "AR": "أُعيد تخزينها",
    },
    "ret_kpi_writeoff": {
        "EN": "WRITTEN OFF",
        "DE": "ABGESCHRIEBEN",
        "AR": "تم شطبها",
    },
    "ret_kpi_refunded": {
        "EN": "TOTAL REFUNDED",
        "DE": "ERSTATTUNGEN",
        "AR": "إجمالي المسترد",
    },
    "ret_empty_title": {
        "EN": "No returns recorded",
        "DE": "Keine Rückgaben",
        "AR": "لا توجد مرتجعات",
    },
    "ret_empty_sub": {
        "EN": "Returns will appear here when processed",
        "DE": "Rückgaben werden hier angezeigt",
        "AR": "ستظهر المرتجعات هنا عند معالجتها",
    },
    "ret_dlg_reason_ph": {
        "EN": "Defective, wrong item, etc.",
        "DE": "Defekt, falscher Artikel, etc.",
        "AR": "معيب، منتج خاطئ، إلخ.",
    },
    "ret_warn_select_item": {
        "EN": "Please select an item.",
        "DE": "Bitte wählen Sie einen Artikel.",
        "AR": "يرجى اختيار منتج.",
    },
    "po_supplier_none": {
        "EN": "— None —",
        "DE": "— Keine —",
        "AR": "— لا يوجد —",
    },
    "po_warn_select_item": {
        "EN": "Please select an item.",
        "DE": "Bitte wählen Sie einen Artikel.",
        "AR": "يرجى اختيار منتج.",
    },
    "po_search_ph": {
        "EN": "Search purchase orders…",
        "DE": "Bestellungen suchen…",
        "AR": "البحث في أوامر الشراء…",
    },
    "col_item": {
        "EN": "Item",
        "DE": "Artikel",
        "AR": "المنتج",
    },
    "col_barcode": {
        "EN": "Barcode",
        "DE": "Barcode",
        "AR": "الباركود",
    },
    "col_stock": {
        "EN": "Stock",
        "DE": "Bestand",
        "AR": "المخزون",
    },
    "analytics_quick_actions": {
        "EN": "QUICK ACTIONS",
        "DE": "SCHNELLAKTIONEN",
        "AR": "إجراءات سريعة",
    },
    "analytics_recent_activity": {
        "EN": "RECENT ACTIVITY",
        "DE": "LETZTE AKTIVITÄTEN",
        "AR": "النشاط الأخير",
    },
    "analytics_no_activity": {
        "EN": "No recent activity",
        "DE": "Keine Aktivitäten",
        "AR": "لا يوجد نشاط حديث",
    },
    "stockops_quick_in": {
        "EN": "Quick +1",
        "DE": "Schnell +1",
        "AR": "إضافة سريعة +1",
    },
    "stockops_quick_out": {
        "EN": "Quick -1",
        "DE": "Schnell -1",
        "AR": "سحب سريع -1",
    },
    "action_close": {
        "EN": "Close",
        "DE": "Schließen",
        "AR": "إغلاق",
    },
    "action_refresh": {
        "EN": "Refresh",
        "DE": "Aktualisieren",
        "AR": "تحديث",
    },
    "btn_save": {
        "EN": "Save",
        "DE": "Speichern",
        "AR": "حفظ",
    },
    "btn_create": {
        "EN": "Create",
        "DE": "Erstellen",
        "AR": "إنشاء",
    },
    "btn_apply": {
        "EN": "Apply",
        "DE": "Anwenden",
        "AR": "تطبيق",
    },
    # ── Order field (was Inventur) ────────────────────────────────────────────
    "disp_dlg_order": {
        "EN": "Set Order Amount",
        "DE": "Bestellmenge festlegen",
        "AR": "تحديد كمية الطلب",
    },
    "disp_order_hint": {
        "EN": "Enter the amount you ordered.\nWhen the delivery arrives, check against this number,\nthen clear it after verification.",
        "DE": "Geben Sie die bestellte Menge ein.\nBei Lieferung mit dieser Zahl abgleichen,\ndanach zurücksetzen.",
        "AR": "أدخل الكمية المطلوبة.\nعند وصول الطلب، تحقق من هذا الرقم،\nثم امسحه بعد التحقق.",
    },
    "disp_order_amount": {
        "EN": "Ordered amount:",
        "DE": "Bestellmenge:",
        "AR": "الكمية المطلوبة:",
    },
    "disp_order_clear": {
        "EN": "Clear Order",
        "DE": "Bestellung löschen",
        "AR": "مسح الطلب",
    },
    "disp_tip_order": {
        "EN": "Double-click to set/clear order amount",
        "DE": "Doppelklick zum Setzen/Löschen der Bestellmenge",
        "AR": "انقر مرتين لتحديد/مسح كمية الطلب",
    },
    # ── Barcode Generator ──────────────────────────────────────────────────────
    "nav_barcode_gen":      {"EN": "Barcodes",                  "DE": "Barcodes",                   "AR": "الباركودات"},
    "bcgen_title":          {"EN": "Barcode Generator",         "DE": "Barcode-Generator",          "AR": "مولد الباركود"},
    "bcgen_scope_all":      {"EN": "All items without barcodes","DE": "Alle ohne Barcode",          "AR": "كل المنتجات بدون باركود"},
    "bcgen_scope_category": {"EN": "By category",              "DE": "Nach Kategorie",              "AR": "حسب الفئة"},
    "bcgen_scope_model":    {"EN": "By model",                 "DE": "Nach Modell",                 "AR": "حسب الطراز"},
    "bcgen_scope_part_type":{"EN": "By part type",             "DE": "Nach Teiletyp",               "AR": "حسب نوع القطعة"},
    "bcgen_format":         {"EN": "Options",                  "DE": "Optionen",                    "AR": "الخيارات"},
    "bcgen_include_commands":{"EN": "Include command barcodes (ADD/DEL/OK)", "DE": "Befehlsbarcodes einschließen", "AR": "تضمين باركودات الأوامر"},
    "bcgen_include_existing":{"EN": "Include items with existing barcodes", "DE": "Artikel mit vorhandenen Barcodes einschließen", "AR": "تضمين المنتجات ذات الباركود الموجود"},
    "bcgen_generate":       {"EN": "Generate Preview",         "DE": "Vorschau generieren",         "AR": "إنشاء معاينة"},
    "bcgen_assign_save":    {"EN": "Assign & Save",            "DE": "Zuweisen & Speichern",        "AR": "تعيين وحفظ"},
    "bcgen_export_pdf":     {"EN": "Export PDF",               "DE": "PDF exportieren",             "AR": "تصدير PDF"},
    "bcgen_print":          {"EN": "Print",                    "DE": "Drucken",                     "AR": "طباعة"},
    "bcgen_preview":        {"EN": "Preview",                  "DE": "Vorschau",                    "AR": "معاينة"},
    "bcgen_page_of":        {"EN": "Page {current} of {total}","DE": "Seite {current} von {total}", "AR": "صفحة {current} من {total}"},
    "bcgen_no_items":       {"EN": "No items found for selected scope", "DE": "Keine Artikel für ausgewählten Bereich", "AR": "لم يتم العثور على منتجات"},
    "bcgen_assigned_n":     {"EN": "{n} barcodes assigned",    "DE": "{n} Barcodes zugewiesen",     "AR": "تم تعيين {n} باركود"},
    # ── StockService error messages ───────────────────────────────────────────
    "err_qty_positive": {
        "EN": "Quantity must be positive",
        "DE": "Menge muss positiv sein",
        "AR": "يجب أن تكون الكمية موجبة",
    },
    "err_entry_not_found": {
        "EN": "Stock entry not found",
        "DE": "Lagereintrag nicht gefunden",
        "AR": "القيد غير موجود",
    },
    "err_insufficient_stock": {
        "EN": "Insufficient stock.  Available: {available}   Requested: {requested}",
        "DE": "Unzureichender Bestand.  Verfügbar: {available}   Angefordert: {requested}",
        "AR": "مخزون غير كافٍ.  المتاح: {available}   المطلوب: {requested}",
    },
    "err_product_not_found": {
        "EN": "Product not found",
        "DE": "Produkt nicht gefunden",
        "AR": "المنتج غير موجود",
    },
    "err_stock_negative": {
        "EN": "Stock cannot be negative",
        "DE": "Bestand kann nicht negativ sein",
        "AR": "لا يمكن أن يكون المخزون سالباً",
    },
    # ── Colors ────────────────────────────────────────────────────────────────
    "clr_title":          {"EN": "COLORS",                       "DE": "FARBEN",                      "AR": "الألوان"},
    "clr_add":            {"EN": "+ Add Color",                  "DE": "+ Farbe hinzufuegen",          "AR": "+ إضافة لون"},
    "clr_hint":           {"EN": "Select a part type to manage colors", "DE": "Teiletyp waehlen um Farben zu verwalten", "AR": "اختر نوع القطعة لإدارة الألوان"},
    "clr_select_title":   {"EN": "Select Color",                "DE": "Farbe waehlen",                "AR": "اختر لون"},
    "clr_select_hdr":     {"EN": "Select Colors to Add",        "DE": "Farben zum Hinzufuegen waehlen", "AR": "اختر الألوان للإضافة"},
    "clr_select_all":     {"EN": "Select All",                  "DE": "Alle waehlen",                 "AR": "تحديد الكل"},
    "clr_add_selected":   {"EN": "Add Selected",                "DE": "Ausgewaehlte hinzufuegen",     "AR": "إضافة المحدد"},
    "clr_all_added":      {"EN": "All colors already added",    "DE": "Alle Farben bereits hinzugefuegt", "AR": "تمت إضافة جميع الألوان"},
    "clr_none":           {"EN": "No colors defined",           "DE": "Keine Farben definiert",       "AR": "لا ألوان محددة"},
    "clr_barcodes_hdr":   {"EN": "Color Barcodes",              "DE": "Farb-Barcodes",                "AR": "باركودات الألوان"},
    "clr_barcodes_hint":  {"EN": "Scan these after a model barcode to select color variant", "DE": "Nach dem Modell-Barcode scannen um Farbvariante auszuwaehlen", "AR": "امسح هذه بعد باركود الطراز لاختيار لون"},
    "icon_choose_title":  {"EN": "Choose Icon",                 "DE": "Symbol waehlen",               "AR": "اختر رمز"},
    "icon_choose_hdr":    {"EN": "Choose Category Icon",        "DE": "Kategorie-Symbol waehlen",     "AR": "اختر رمز الفئة"},
    "footer_connected":   {"EN": "Connected",                   "DE": "Verbunden",                    "AR": "متصل"},
    # ── Backup & Restore ────────────────────────────────────────────────────────
    "backup_tab_title": {"EN": "Backup & Restore", "DE": "Sicherung & Wiederherstellung", "AR": "النسخ الاحتياطي والاستعادة"},
    "backup_create": {"EN": "Create Backup", "DE": "Sicherung erstellen", "AR": "إنشاء نسخة احتياطية"},
    "backup_restore": {"EN": "Restore Backup", "DE": "Sicherung wiederherstellen", "AR": "استعادة نسخة احتياطية"},
    "backup_delete": {"EN": "Delete Backup", "DE": "Sicherung löschen", "AR": "حذف النسخة الاحتياطية"},
    "backup_created_ok": {"EN": "Backup created successfully", "DE": "Sicherung erfolgreich erstellt", "AR": "تم إنشاء النسخة الاحتياطية بنجاح"},
    "backup_restored_ok": {"EN": "Backup restored. Restart the app.", "DE": "Sicherung wiederhergestellt. App neu starten.", "AR": "تم استعادة النسخة. أعد تشغيل التطبيق."},
    "backup_confirm_restore": {"EN": "This will replace ALL current data. Continue?", "DE": "Alle aktuellen Daten werden ersetzt. Fortfahren?", "AR": "سيتم استبدال جميع البيانات الحالية. متابعة؟"},
    "backup_confirm_delete": {"EN": "Delete this backup permanently?", "DE": "Diese Sicherung endgültig löschen?", "AR": "حذف هذه النسخة نهائياً؟"},
    "backup_none": {"EN": "No backups found", "DE": "Keine Sicherungen gefunden", "AR": "لا توجد نسخ احتياطية"},
    "backup_location": {"EN": "Backup Location", "DE": "Speicherort", "AR": "موقع النسخ الاحتياطي"},
    "backup_open_folder": {"EN": "Open Folder", "DE": "Ordner öffnen", "AR": "فتح المجلد"},
    "backup_col_date": {"EN": "Date", "DE": "Datum", "AR": "التاريخ"},
    "backup_col_size": {"EN": "Size", "DE": "Größe", "AR": "الحجم"},
    "backup_col_file": {"EN": "File", "DE": "Datei", "AR": "الملف"},
    # ── Import / Export ──────────────────────────────────────────────────────────
    "export_title": {
        "EN": "Export Data",
        "DE": "Daten exportieren",
        "AR": "تصدير البيانات",
    },
    "export_inventory": {
        "EN": "Export Inventory",
        "DE": "Inventar exportieren",
        "AR": "تصدير المخزون",
    },
    "export_transactions": {
        "EN": "Export Transactions",
        "DE": "Transaktionen exportieren",
        "AR": "تصدير المعاملات",
    },
    "export_low_stock": {
        "EN": "Export Low Stock",
        "DE": "Niedrigen Bestand exportieren",
        "AR": "تصدير المخزون المنخفض",
    },
    "export_success": {
        "EN": "Export saved to {path}",
        "DE": "Export gespeichert unter {path}",
        "AR": "تم حفظ التصدير في {path}",
    },
    "export_error": {
        "EN": "Export failed: {err}",
        "DE": "Export fehlgeschlagen: {err}",
        "AR": "فشل التصدير: {err}",
    },
    "import_title": {
        "EN": "Import Data",
        "DE": "Daten importieren",
        "AR": "استيراد البيانات",
    },
    "import_success": {
        "EN": "Imported {count} items",
        "DE": "{count} Einträge importiert",
        "AR": "تم استيراد {count} عنصر",
    },
    "import_error": {
        "EN": "Import failed: {err}",
        "DE": "Import fehlgeschlagen: {err}",
        "AR": "فشل الاستيراد: {err}",
    },
    "import_preview": {
        "EN": "Preview ({count} rows)",
        "DE": "Vorschau ({count} Zeilen)",
        "AR": "معاينة ({count} صف)",
    },
    "import_col_mapping": {
        "EN": "Column Mapping",
        "DE": "Spaltenzuordnung",
        "AR": "تعيين الأعمدة",
    },
    "import_skip_first": {
        "EN": "Skip header row",
        "DE": "Kopfzeile überspringen",
        "AR": "تخطي صف العنوان",
    },

    # ── Backup & Restore Tab ──
    "admin_tab_backup": {
        "EN": "Backup & Restore",
        "DE": "Sichern & Wiederherstellen",
        "AR": "النسخة الاحتياطية والاستعادة",
    },
    "backup_title": {
        "EN": "Backup & Restore",
        "DE": "Sichern & Wiederherstellen",
        "AR": "النسخة الاحتياطية والاستعادة",
    },
    "backup_desc": {
        "EN": "Create and manage database backups. Backups are stored in a backups/ folder next to the database.",
        "DE": "Erstellen und verwalten Sie Datenbanksicherungen. Sicherungen werden in einem backups/-Ordner neben der Datenbank gespeichert.",
        "AR": "إنشاء وإدارة النسخ الاحتياطية للقاعدة البيانات. يتم تخزين النسخ الاحتياطية في مجلد النسخ الاحتياطية بجانب قاعدة البيانات.",
    },
    "backup_create_btn": {
        "EN": "Create Backup Now",
        "DE": "Sicherung jetzt erstellen",
        "AR": "إنشاء نسخة احتياطية الآن",
    },
    "backup_list_label": {
        "EN": "Available Backups",
        "DE": "Verfügbare Sicherungen",
        "AR": "النسخ الاحتياطية المتاحة",
    },
    "backup_col_date": {
        "EN": "Date",
        "DE": "Datum",
        "AR": "التاريخ",
    },
    "backup_col_size": {
        "EN": "Size",
        "DE": "Größe",
        "AR": "الحجم",
    },
    "backup_col_file": {
        "EN": "File",
        "DE": "Datei",
        "AR": "الملف",
    },
    "backup_restore_btn": {
        "EN": "Restore Selected",
        "DE": "Ausgewählte wiederherstellen",
        "AR": "استعادة المحدد",
    },
    "backup_delete_btn": {
        "EN": "Delete Selected",
        "DE": "Ausgewählte löschen",
        "AR": "حذف المحدد",
    },
    "backup_open_folder_btn": {
        "EN": "Open Folder",
        "DE": "Ordner öffnen",
        "AR": "فتح المجلد",
    },
    "backup_created": {
        "EN": "Backup created: {path}",
        "DE": "Sicherung erstellt: {path}",
        "AR": "تم إنشاء النسخة الاحتياطية: {path}",
    },
    "backup_error_title": {
        "EN": "Error",
        "DE": "Fehler",
        "AR": "خطأ",
    },
    "backup_error_create": {
        "EN": "Failed to create backup: {error}",
        "DE": "Fehler beim Erstellen der Sicherung: {error}",
        "AR": "فشل إنشاء النسخة الاحتياطية: {error}",
    },
    "backup_warning_title": {
        "EN": "Warning",
        "DE": "Warnung",
        "AR": "تحذير",
    },
    "backup_select_to_restore": {
        "EN": "Please select a backup to restore",
        "DE": "Bitte wählen Sie eine Sicherung zum Wiederherstellen",
        "AR": "يرجى تحديد نسخة احتياطية لاستعادتها",
    },
    "backup_confirm_restore_title": {
        "EN": "Confirm Restore",
        "DE": "Wiederherstellung bestätigen",
        "AR": "تأكيد الاستعادة",
    },
    "backup_confirm_restore_msg": {
        "EN": "Restore database from backup '{filename}'? This will replace the current database.",
        "DE": "Datenbank aus der Sicherung '{filename}' wiederherstellen? Dies ersetzt die aktuelle Datenbank.",
        "AR": "استعادة قاعدة البيانات من النسخة الاحتياطية '{filename}'؟ سيؤدي هذا إلى استبدال قاعدة البيانات الحالية.",
    },
    "backup_restored_msg": {
        "EN": "Database restored successfully",
        "DE": "Datenbank erfolgreich wiederhergestellt",
        "AR": "تم استعادة قاعدة البيانات بنجاح",
    },
    "backup_success_title": {
        "EN": "Success",
        "DE": "Erfolg",
        "AR": "نجح",
    },
    "backup_restored_success": {
        "EN": "Database restored from '{filename}'. The application may need to be restarted.",
        "DE": "Datenbank aus '{filename}' wiederhergestellt. Die Anwendung muss möglicherweise neu gestartet werden.",
        "AR": "تم استعادة قاعدة البيانات من '{filename}'. قد يكون من الضروري إعادة تشغيل التطبيق.",
    },
    "backup_error_restore": {
        "EN": "Failed to restore backup: {error}",
        "DE": "Fehler beim Wiederherstellen der Sicherung: {error}",
        "AR": "فشلت استعادة النسخة الاحتياطية: {error}",
    },
    "backup_select_to_delete": {
        "EN": "Please select a backup to delete",
        "DE": "Bitte wählen Sie eine Sicherung zum Löschen",
        "AR": "يرجى تحديد نسخة احتياطية لحذفها",
    },
    "backup_confirm_delete_title": {
        "EN": "Confirm Delete",
        "DE": "Löschung bestätigen",
        "AR": "تأكيد الحذف",
    },
    "backup_confirm_delete_msg": {
        "EN": "Delete backup '{filename}'? This action cannot be undone.",
        "DE": "Sicherung '{filename}' löschen? Diese Aktion kann nicht rückgängig gemacht werden.",
        "AR": "حذف النسخة الاحتياطية '{filename}'؟ لا يمكن التراجع عن هذا الإجراء.",
    },
    "backup_deleted_msg": {
        "EN": "Backup deleted",
        "DE": "Sicherung gelöscht",
        "AR": "تم حذف النسخة الاحتياطية",
    },
    "backup_error_delete": {
        "EN": "Failed to delete backup: {error}",
        "DE": "Fehler beim Löschen der Sicherung: {error}",
        "AR": "فشل حذف النسخة الاحتياطية: {error}",
    },

    # ── Import/Export Tab ──
    "admin_tab_import_export": {
        "EN": "Import/Export",
        "DE": "Importieren/Exportieren",
        "AR": "الاستيراد/التصدير",
    },
    "import_export_title": {
        "EN": "Import & Export",
        "DE": "Importieren & Exportieren",
        "AR": "الاستيراد والتصدير",
    },
    "export_section_label": {
        "EN": "Export Data",
        "DE": "Daten exportieren",
        "AR": "تصدير البيانات",
    },
    "export_inventory_btn": {
        "EN": "Export Inventory CSV",
        "DE": "Bestand CSV exportieren",
        "AR": "تصدير المخزون CSV",
    },
    "export_transactions_btn": {
        "EN": "Export Transactions CSV",
        "DE": "Transaktionen CSV exportieren",
        "AR": "تصدير المعاملات CSV",
    },
    "export_low_stock_btn": {
        "EN": "Export Low Stock CSV",
        "DE": "Niedriger Bestand CSV exportieren",
        "AR": "تصدير المخزون المنخفض CSV",
    },
    "export_inventory_dialog": {
        "EN": "Export Inventory",
        "DE": "Bestand exportieren",
        "AR": "تصدير المخزون",
    },
    "export_transactions_dialog": {
        "EN": "Export Transactions",
        "DE": "Transaktionen exportieren",
        "AR": "تصدير المعاملات",
    },
    "export_low_stock_dialog": {
        "EN": "Export Low Stock Items",
        "DE": "Artikel mit niedrigem Bestand exportieren",
        "AR": "تصدير العناصر ذات المخزون المنخفض",
    },
    "export_success": {
        "EN": "Exported: {filename}",
        "DE": "Exportiert: {filename}",
        "AR": "تم التصدير: {filename}",
    },
    "export_success_title": {
        "EN": "Export Successful",
        "DE": "Export erfolgreich",
        "AR": "نجح التصدير",
    },
    "export_file_saved": {
        "EN": "File saved to: {path}",
        "DE": "Datei gespeichert in: {path}",
        "AR": "تم حفظ الملف في: {path}",
    },
    "export_error": {
        "EN": "Export failed",
        "DE": "Export fehlgeschlagen",
        "AR": "فشل التصدير",
    },
    "export_error_title": {
        "EN": "Export Error",
        "DE": "Exportfehler",
        "AR": "خطأ في التصدير",
    },
    "export_error_msg": {
        "EN": "Export error: {error}",
        "DE": "Exportfehler: {error}",
        "AR": "خطأ في التصدير: {error}",
    },
    "import_section_label": {
        "EN": "Import Products",
        "DE": "Produkte importieren",
        "AR": "استيراد المنتجات",
    },
    "import_select_file_btn": {
        "EN": "Select CSV File",
        "DE": "CSV-Datei auswählen",
        "AR": "اختر ملف CSV",
    },
    "import_select_file_dialog": {
        "EN": "Select CSV to Import",
        "DE": "CSV zum Importieren auswählen",
        "AR": "اختر CSV للاستيراد",
    },
    "import_no_file": {
        "EN": "No file selected",
        "DE": "Keine Datei ausgewählt",
        "AR": "لم يتم تحديد ملف",
    },
    "import_preview_label": {
        "EN": "Preview (first 10 rows)",
        "DE": "Vorschau (erste 10 Zeilen)",
        "AR": "معاينة (أول 10 صفوف)",
    },
    "import_column_mapping_label": {
        "EN": "Column Mapping",
        "DE": "Spaltenzuordnung",
        "AR": "تعيين الأعمدة",
    },
    "import_col_brand": {
        "EN": "Brand",
        "DE": "Marke",
        "AR": "الماركة",
    },
    "import_col_name": {
        "EN": "Name",
        "DE": "Name",
        "AR": "الاسم",
    },
    "import_col_color": {
        "EN": "Color",
        "DE": "Farbe",
        "AR": "اللون",
    },
    "import_col_barcode": {
        "EN": "Barcode",
        "DE": "Barcode",
        "AR": "الباركود",
    },
    "import_col_stock": {
        "EN": "Stock",
        "DE": "Bestand",
        "AR": "المخزون",
    },
    "import_col_min_stock": {
        "EN": "Min Stock",
        "DE": "Mindestbestand",
        "AR": "الحد الأدنى",
    },
    "import_col_price": {
        "EN": "Price",
        "DE": "Preis",
        "AR": "السعر",
    },
    "import_skip_header_cb": {
        "EN": "Skip header row",
        "DE": "Kopfzeile überspringen",
        "AR": "تخطي صف العنوان",
    },
    "import_execute_btn": {
        "EN": "Import Products",
        "DE": "Produkte importieren",
        "AR": "استيراد المنتجات",
    },
    "import_warning_title": {
        "EN": "Warning",
        "DE": "Warnung",
        "AR": "تحذير",
    },
    "import_select_file_first": {
        "EN": "Please select a CSV file first",
        "DE": "Bitte wählen Sie zuerst eine CSV-Datei",
        "AR": "يرجى تحديد ملف CSV أولاً",
    },
    "import_missing_required_cols": {
        "EN": "Brand and Name columns are required",
        "DE": "Spalten Marke und Name sind erforderlich",
        "AR": "أعمدة الماركة والاسم مطلوبة",
    },
    "import_result_summary": {
        "EN": "Imported: {imported}, Skipped: {skipped}, Errors: {errors}",
        "DE": "Importiert: {imported}, Übersprungen: {skipped}, Fehler: {errors}",
        "AR": "تم الاستيراد: {imported}، تم التخطي: {skipped}، أخطاء: {errors}",
    },
    "import_partial_title": {
        "EN": "Import Completed with Errors",
        "DE": "Import mit Fehlern abgeschlossen",
        "AR": "اكتمل الاستيراد مع أخطاء",
    },
    "import_partial_msg": {
        "EN": "Successfully imported {imported} products, but {errors} rows had errors",
        "DE": "Es wurden {imported} Produkte erfolgreich importiert, aber {errors} Zeilen hatten Fehler",
        "AR": "تم استيراد {imported} منتج بنجاح، لكن {errors} صف بها أخطاء",
    },
    "import_success_title": {
        "EN": "Import Successful",
        "DE": "Import erfolgreich",
        "AR": "نجح الاستيراد",
    },
    "import_success_msg": {
        "EN": "Successfully imported {count} products",
        "DE": "{count} Produkte erfolgreich importiert",
        "AR": "تم استيراد {count} منتج بنجاح",
    },
    "import_error_title": {
        "EN": "Import Error",
        "DE": "Importfehler",
        "AR": "خطأ في الاستيراد",
    },
    "import_error_msg": {
        "EN": "Import error: {error}",
        "DE": "Importfehler: {error}",
        "AR": "خطأ في الاستيراد: {error}",
    },

    # ── Database Tools Tab ────────────────────────────────────────────────────────
    "admin_tab_db_tools": {
        "EN": "Database Tools",
        "DE": "Datenbank-Tools",
        "AR": "أدوات قاعدة البيانات",
    },
    "db_tools_info_title": {
        "EN": "Database Information",
        "DE": "Datenbank-Informationen",
        "AR": "معلومات قاعدة البيانات",
    },
    "db_tools_file_path": {
        "EN": "File Path",
        "DE": "Dateipfad",
        "AR": "مسار الملف",
    },
    "db_tools_file_size": {
        "EN": "File Size",
        "DE": "Dateigröße",
        "AR": "حجم الملف",
    },
    "db_tools_schema_ver": {
        "EN": "Schema Version",
        "DE": "Schema-Version",
        "AR": "إصدار المخطط",
    },
    "db_tools_optimize": {
        "EN": "Optimize Database",
        "DE": "Datenbank optimieren",
        "AR": "تحسين قاعدة البيانات",
    },
    "db_tools_optimize_desc": {
        "EN": "Run SQLite optimizer and reclaim unused space",
        "DE": "SQLite-Optimierer ausführen und ungenutzten Speicher freigeben",
        "AR": "تشغيل محسن SQLite واستعادة المساحة غير المستخدمة",
    },
    "db_tools_integrity": {
        "EN": "Integrity Check",
        "DE": "Integritätsprüfung",
        "AR": "فحص السلامة",
    },
    "db_tools_integrity_desc": {
        "EN": "Verify database structure is intact",
        "DE": "Datenbankstruktur auf Integrität prüfen",
        "AR": "التحقق من سلامة هيكل قاعدة البيانات",
    },
    "db_tools_result_ok": {
        "EN": "Database is healthy",
        "DE": "Datenbank ist in Ordnung",
        "AR": "قاعدة البيانات سليمة",
    },
    "db_tools_result_optimized": {
        "EN": "Database optimized successfully",
        "DE": "Datenbank erfolgreich optimiert",
        "AR": "تم تحسين قاعدة البيانات بنجاح",
    },

    # ── Filters ───────────────────────────────────────────────────────────────────
    "filter_search_placeholder": {
        "EN": "Search by name, barcode, brand...",
        "DE": "Suche nach Name, Barcode, Marke...",
        "AR": "بحث بالاسم، الباركود، العلامة...",
    },
    "filter_all_status": {
        "EN": "All Status",
        "DE": "Alle Status",
        "AR": "جميع الحالات",
    },
    "filter_reset": {
        "EN": "Reset",
        "DE": "Zurücksetzen",
        "AR": "إعادة تعيين",
    },
    "filter_advanced": {
        "EN": "Advanced",
        "DE": "Erweitert",
        "AR": "متقدم",
    },
    "filter_category_label": {
        "EN": "Category:",
        "DE": "Kategorie:",
        "AR": "الفئة:",
    },
    "filter_all_categories": {
        "EN": "All Categories",
        "DE": "Alle Kategorien",
        "AR": "جميع الفئات",
    },
    "filter_products_only": {
        "EN": "Products Only",
        "DE": "Nur Produkte",
        "AR": "المنتجات فقط",
    },
    "filter_price_label": {
        "EN": "Price:",
        "DE": "Preis:",
        "AR": "السعر:",
    },
    "filter_price_from": {
        "EN": "From",
        "DE": "Von",
        "AR": "من",
    },
    "filter_price_to": {
        "EN": "To",
        "DE": "Bis",
        "AR": "إلى",
    },
    "filter_price_min": {
        "EN": "Min",
        "DE": "Min",
        "AR": "الحد الأدنى",
    },
    "filter_price_max": {
        "EN": "Max",
        "DE": "Max",
        "AR": "الحد الأقصى",
    },
    # ── Product image ───────────────────────────────────────────────────────
    "dlg_lbl_image": {
        "EN": "Image",
        "DE": "Bild",
        "AR": "صورة",
    },
    "dlg_image_browse": {
        "EN": "Browse…",
        "DE": "Durchsuchen…",
        "AR": "استعراض…",
    },
    "dlg_image_remove": {
        "EN": "Remove",
        "DE": "Entfernen",
        "AR": "إزالة",
    },
    "dlg_image_filter": {
        "EN": "Images (*.jpg *.jpeg *.png *.webp *.bmp)",
        "DE": "Bilder (*.jpg *.jpeg *.png *.webp *.bmp)",
        "AR": "صور (*.jpg *.jpeg *.png *.webp *.bmp)",
    },
    "dlg_image_no_image": {
        "EN": "No image",
        "DE": "Kein Bild",
        "AR": "لا توجد صورة",
    },
    # ── Help system ─────────────────────────────────────────────────────────
    "nav_help": {
        "EN": "Help",
        "DE": "Hilfe",
        "AR": "مساعدة",
    },
    "help_title": {
        "EN": "Help — Stock Manager Pro",
        "DE": "Hilfe — Lagerverwaltung Pro",
        "AR": "مساعدة — مدير المخزون",
    },
    "help_getting_started": {
        "EN": "Getting Started",
        "DE": "Erste Schritte",
        "AR": "البدء",
    },
    "help_getting_started_body": {
        "EN": "Welcome to Stock Manager Pro! Use the sidebar to navigate between sections:\n\n"
              "• **Dashboard** — Overview of inventory health, low-stock alerts, and value\n"
              "• **Inventory** — Browse, search, add, and edit products\n"
              "• **Categories** — Manage phone model × part type matrix grids\n"
              "• **Transactions** — Full audit trail of all stock movements\n"
              "• **Stock Operations** — Bulk stock-in, stock-out, and adjustments\n"
              "• **Quick Scan** — Barcode scanner for fast operations\n"
              "• **Reports** — Generate PDF reports, audit sheets, and barcode labels",
        "DE": "Willkommen bei Lagerverwaltung Pro! Nutzen Sie die Seitenleiste zur Navigation:\n\n"
              "• **Dashboard** — Übersicht über Bestandsgesundheit und Warnungen\n"
              "• **Inventar** — Produkte durchsuchen, hinzufügen und bearbeiten\n"
              "• **Kategorien** — Modell × Teiletyp-Matrixgitter verwalten\n"
              "• **Transaktionen** — Vollständiges Protokoll aller Bestandsbewegungen\n"
              "• **Bestandsoperationen** — Massen-Ein-/Ausbuchung und Korrekturen\n"
              "• **Quick Scan** — Barcode-Scanner für schnelle Operationen\n"
              "• **Berichte** — PDF-Berichte, Inventurbögen und Barcode-Etiketten",
        "AR": "مرحبًا بك في مدير المخزون! استخدم الشريط الجانبي للتنقل:\n\n"
              "• **لوحة المعلومات** — نظرة عامة على حالة المخزون والتنبيهات\n"
              "• **المخزون** — تصفح المنتجات وإضافتها وتعديلها\n"
              "• **الفئات** — إدارة شبكات الموديل × نوع القطعة\n"
              "• **المعاملات** — سجل كامل لجميع حركات المخزون\n"
              "• **عمليات المخزون** — إدخال وإخراج وتعديل جماعي\n"
              "• **المسح السريع** — ماسح الباركود للعمليات السريعة\n"
              "• **التقارير** — تقارير PDF وأوراق الجرد وملصقات الباركود",
    },
    "help_products": {
        "EN": "Managing Products",
        "DE": "Produkte verwalten",
        "AR": "إدارة المنتجات",
    },
    "help_products_body": {
        "EN": "**Add a product:** Click the + button or use Ctrl+N. Fill in brand, type, color, "
              "and optional barcode. You can also attach a product image.\n\n"
              "**Edit a product:** Select it in the table, then click the edit button or double-click.\n\n"
              "**Stock operations:** Select a product and use Stock In (↑), Stock Out (↓), or Adjust (⇅).\n\n"
              "**Search:** Type in the search bar to filter by brand, name, color, or barcode. "
              "Use Advanced Filters for category and price range filtering.",
        "DE": "**Produkt hinzufügen:** Klicken Sie auf + oder Strg+N. Füllen Sie Marke, Typ, Farbe "
              "und optionalen Barcode aus. Sie können auch ein Produktbild anhängen.\n\n"
              "**Produkt bearbeiten:** Wählen Sie es in der Tabelle aus und klicken Sie auf Bearbeiten.\n\n"
              "**Bestandsoperationen:** Wählen Sie ein Produkt und verwenden Sie Einbuchen (↑), Ausbuchen (↓) oder Korrektur (⇅).\n\n"
              "**Suche:** Tippen Sie in die Suchleiste, um nach Marke, Name, Farbe oder Barcode zu filtern.",
        "AR": "**إضافة منتج:** انقر على زر + أو استخدم Ctrl+N. أدخل العلامة التجارية والنوع واللون والباركود الاختياري.\n\n"
              "**تعديل منتج:** حدده في الجدول ثم انقر على زر التعديل.\n\n"
              "**عمليات المخزون:** حدد منتجًا واستخدم إدخال (↑) أو إخراج (↓) أو تعديل (⇅).\n\n"
              "**البحث:** اكتب في شريط البحث للتصفية حسب العلامة التجارية أو الاسم أو اللون أو الباركود.",
    },
    "help_shortcuts": {
        "EN": "Keyboard Shortcuts",
        "DE": "Tastenkürzel",
        "AR": "اختصارات لوحة المفاتيح",
    },
    "help_shortcuts_body": {
        "EN": "• **Ctrl+N** — New product\n"
              "• **Ctrl+F** — Focus search bar\n"
              "• **Ctrl+B** — Focus barcode scanner\n"
              "• **Delete** — Delete selected product\n"
              "• **F1** — Open this help dialog",
        "DE": "• **Strg+N** — Neues Produkt\n"
              "• **Strg+F** — Suchleiste fokussieren\n"
              "• **Strg+B** — Barcode-Scanner fokussieren\n"
              "• **Entf** — Ausgewähltes Produkt löschen\n"
              "• **F1** — Diese Hilfe öffnen",
        "AR": "• **Ctrl+N** — منتج جديد\n"
              "• **Ctrl+F** — التركيز على شريط البحث\n"
              "• **Ctrl+B** — التركيز على ماسح الباركود\n"
              "• **Delete** — حذف المنتج المحدد\n"
              "• **F1** — فتح نافذة المساعدة",
    },
    "help_about": {
        "EN": "About",
        "DE": "Über",
        "AR": "حول",
    },
    "help_about_body": {
        "EN": "**Stock Manager Pro** v1.0\n\n"
              "A professional inventory management application for Windows.\n"
              "Supports English, German, and Arabic (RTL).\n\n"
              "Built with Python, PyQt6, and SQLite.",
        "DE": "**Lagerverwaltung Pro** v1.0\n\n"
              "Eine professionelle Lagerverwaltungsanwendung für Windows.\n"
              "Unterstützt Englisch, Deutsch und Arabisch (RTL).\n\n"
              "Erstellt mit Python, PyQt6 und SQLite.",
        "AR": "**مدير المخزون** الإصدار 1.0\n\n"
              "تطبيق احترافي لإدارة المخزون لنظام Windows.\n"
              "يدعم الإنجليزية والألمانية والعربية (RTL).\n\n"
              "مبني باستخدام Python وPyQt6 وSQLite.",
    },
    # ── Help: Categories & Matrix ───────────────────────────────────────────
    "help_categories": {
        "EN": "Categories & Matrix Grid",
        "DE": "Kategorien & Matrix-Raster",
        "AR": "الفئات وشبكة المصفوفة",
    },
    "help_categories_body": {
        "EN": "The **Categories** system organises your inventory into groups like Displays, Batteries, "
              "Cases, Charging Ports, etc. Each category appears as its own tab in the sidebar.\n\n"
              "**Matrix grid** — Inside each category you see a spreadsheet-like matrix:\n"
              "• **Rows** = Phone models, grouped by brand (Samsung, Apple, Huawei …)\n"
              "• **Columns** = Part types (e.g. Original, Compatible, Premium), each with its own colour band\n"
              "• **Each cell** shows four fields: Stamm (min-stock), Best (expected), Stock (current), Order (needed)\n\n"
              "**How to use the matrix:**\n"
              "• Click any **stock cell** to open a Stock-In / Stock-Out / Adjust dialog\n"
              "• Click a **Stamm cell** to set the minimum-stock threshold for that item\n"
              "• Use the **Brand filter** dropdown at the top to narrow visible models\n"
              "• Click **Add Model** to register a new phone model (brand + name)\n"
              "• The colour legend bar at the top shows which colour belongs to which part type\n\n"
              "**Barcodes in matrix:** When performing a stock operation from the matrix, you can also "
              "assign or update the barcode for that item directly in the dialog.",
        "DE": "Das **Kategorien**-System organisiert Ihr Inventar in Gruppen wie Displays, Akkus, "
              "Hüllen, Ladeanschlüsse usw. Jede Kategorie erscheint als eigener Tab in der Seitenleiste.\n\n"
              "**Matrix-Raster** — Innerhalb jeder Kategorie sehen Sie ein tabellenartiges Raster:\n"
              "• **Zeilen** = Telefonmodelle, gruppiert nach Marke\n"
              "• **Spalten** = Teiletypen (z.B. Original, Kompatibel, Premium), jeweils mit eigener Farbkennzeichnung\n"
              "• **Jede Zelle** zeigt vier Felder: Stamm (Mindestbestand), Best (erwartet), Bestand (aktuell), Bestellen (benötigt)\n\n"
              "**Nutzung des Rasters:**\n"
              "• Klicken Sie auf eine **Bestandszelle** für Ein-/Ausbuchung/Korrektur\n"
              "• Klicken Sie auf eine **Stamm-Zelle** um den Mindestbestand festzulegen\n"
              "• Verwenden Sie den **Markenfilter** oben, um sichtbare Modelle einzuschränken\n"
              "• Klicken Sie auf **Modell hinzufügen** um ein neues Telefonmodell zu erstellen\n"
              "• Die Farblegende oben zeigt, welche Farbe zu welchem Teiletyp gehört",
        "AR": "نظام **الفئات** ينظم مخزونك في مجموعات مثل الشاشات والبطاريات والأغلفة ومنافذ الشحن وغيرها. "
              "كل فئة تظهر كعلامة تبويب خاصة في الشريط الجانبي.\n\n"
              "**شبكة المصفوفة** — داخل كل فئة ترى جدولاً يشبه جدول البيانات:\n"
              "• **الصفوف** = موديلات الهواتف، مجمعة حسب العلامة التجارية\n"
              "• **الأعمدة** = أنواع القطع (مثل أصلي، متوافق، ممتاز)، كل منها بلون مميز\n"
              "• **كل خلية** تعرض أربعة حقول: الحد الأدنى، المتوقع، المخزون الحالي، المطلوب\n\n"
              "**كيفية استخدام المصفوفة:**\n"
              "• انقر على أي **خلية مخزون** لفتح نافذة إدخال/إخراج/تعديل\n"
              "• انقر على **خلية الحد الأدنى** لتعيين حد المخزون الأدنى\n"
              "• استخدم **فلتر العلامة التجارية** في الأعلى لتضييق الموديلات المرئية\n"
              "• انقر على **إضافة موديل** لتسجيل موديل هاتف جديد",
    },
    # ── Help: Part Types ────────────────────────────────────────────────────
    "help_part_types": {
        "EN": "Part Types & Colours",
        "DE": "Teiletypen & Farben",
        "AR": "أنواع القطع والألوان",
    },
    "help_part_types_body": {
        "EN": "**Part types** are the column groups inside each category. For example, in the \"Displays\" "
              "category you might have part types: Original, Compatible, OLED, TFT.\n\n"
              "**Managing part types (Admin → Part Types):**\n"
              "• **Add** a new part type — give it a name (in all 3 languages) and assign a colour\n"
              "• **Colour assignment** — Each part type gets a visual accent colour shown as a band "
              "in the matrix header. This makes it easy to scan the grid quickly\n"
              "• **Reorder** — Drag part types to change column order in the matrix\n"
              "• **Delete** — You can only delete a part type that has zero stock across all models. "
              "If any items still have stock, you must zero them out first\n\n"
              "**Part type colours vs product colours:** Part type colours are visual labels for the matrix "
              "columns. Product colours (in standalone products) describe the physical item colour (Black, White, Red …).",
        "DE": "**Teiletypen** sind die Spaltengruppen innerhalb jeder Kategorie. Z.B. könnten Sie in der "
              "Kategorie \"Displays\" die Teiletypen haben: Original, Kompatibel, OLED, TFT.\n\n"
              "**Teiletypen verwalten (Admin → Teiletypen):**\n"
              "• **Hinzufügen** — Name in allen 3 Sprachen eingeben und Farbe zuweisen\n"
              "• **Farbzuweisung** — Jeder Teiletyp bekommt eine Akzentfarbe als Band im Matrix-Header\n"
              "• **Neuordnen** — Teiletypen per Drag & Drop in der Spaltenreihenfolge ändern\n"
              "• **Löschen** — Nur möglich wenn der Bestand bei allen Modellen null ist\n\n"
              "**Teiletyp-Farben vs. Produktfarben:** Teiletyp-Farben sind visuelle Kennzeichnungen. "
              "Produktfarben beschreiben die physische Farbe des Artikels.",
        "AR": "**أنواع القطع** هي مجموعات الأعمدة داخل كل فئة. على سبيل المثال، في فئة \"الشاشات\" "
              "قد يكون لديك: أصلي، متوافق، OLED، TFT.\n\n"
              "**إدارة أنواع القطع (المسؤول → أنواع القطع):**\n"
              "• **إضافة** نوع جديد — أدخل الاسم بجميع اللغات الثلاث وعيّن لوناً\n"
              "• **تعيين الألوان** — كل نوع يحصل على لون مميز يظهر في رأس المصفوفة\n"
              "• **إعادة الترتيب** — اسحب أنواع القطع لتغيير ترتيب الأعمدة\n"
              "• **الحذف** — ممكن فقط إذا كان المخزون صفراً في جميع الموديلات",
    },
    # ── Help: Stock Operations ──────────────────────────────────────────────
    "help_stock_ops": {
        "EN": "Stock Operations",
        "DE": "Bestandsoperationen",
        "AR": "عمليات المخزون",
    },
    "help_stock_ops_body": {
        "EN": "The **Stock Operations** tab is a dedicated workspace for professional stock management "
              "outside the matrix view.\n\n"
              "**Layout:**\n"
              "• **Left panel** — Searchable list of all inventory items. Type to filter by name or barcode\n"
              "• **Right panel** — Detail card for the selected item plus the operation form\n\n"
              "**How to perform an operation:**\n"
              "1. Search for the item by name or scan its barcode\n"
              "2. Click the item in the left table\n"
              "3. The right panel shows: current stock, price, status, min-stock info\n"
              "4. Choose an operation: **Stock In** (↑), **Stock Out** (↓), or **Adjust** (⇅)\n"
              "5. Enter the quantity and an optional note\n"
              "6. Click **Apply** — the operation is recorded instantly\n\n"
              "**Recent transactions:** Below the operation form you can see the last 5 operations "
              "on the selected item for quick reference.\n\n"
              "**Tip:** You can also do stock operations directly from the Inventory page by selecting "
              "a product and using the action buttons in the detail panel.",
        "DE": "Der Tab **Bestandsoperationen** ist ein Arbeitsbereich für professionelles Bestandsmanagement.\n\n"
              "**Aufbau:**\n"
              "• **Linkes Panel** — Durchsuchbare Liste aller Artikel. Tippen um nach Name oder Barcode zu filtern\n"
              "• **Rechtes Panel** — Detailkarte des ausgewählten Artikels plus Operationsformular\n\n"
              "**So führen Sie eine Operation durch:**\n"
              "1. Suchen Sie den Artikel oder scannen Sie seinen Barcode\n"
              "2. Klicken Sie auf den Artikel in der linken Tabelle\n"
              "3. Das rechte Panel zeigt: Bestand, Preis, Status, Mindestbestand\n"
              "4. Wählen Sie: **Einbuchen** (↑), **Ausbuchen** (↓) oder **Korrektur** (⇅)\n"
              "5. Geben Sie Menge und optionale Notiz ein\n"
              "6. Klicken Sie auf **Anwenden**",
        "AR": "علامة تبويب **عمليات المخزون** هي مساحة عمل مخصصة لإدارة المخزون المهنية.\n\n"
              "**التخطيط:**\n"
              "• **اللوحة اليسرى** — قائمة قابلة للبحث لجميع عناصر المخزون\n"
              "• **اللوحة اليمنى** — بطاقة تفاصيل العنصر المحدد بالإضافة إلى نموذج العملية\n\n"
              "**كيفية تنفيذ عملية:**\n"
              "1. ابحث عن العنصر بالاسم أو امسح الباركود\n"
              "2. انقر على العنصر في الجدول الأيسر\n"
              "3. اللوحة اليمنى تعرض: المخزون الحالي والسعر والحالة\n"
              "4. اختر العملية: **إدخال** (↑) أو **إخراج** (↓) أو **تعديل** (⇅)\n"
              "5. أدخل الكمية وملاحظة اختيارية\n"
              "6. انقر على **تطبيق**",
    },
    # ── Help: Quick Scan ────────────────────────────────────────────────────
    "help_quick_scan": {
        "EN": "Quick Scan (Barcode Scanner)",
        "DE": "Schnellscan (Barcode-Scanner)",
        "AR": "المسح السريع (ماسح الباركود)",
    },
    "help_quick_scan_body": {
        "EN": "**Quick Scan** is designed for fast barcode-driven batch operations using a USB or "
              "Bluetooth barcode scanner.\n\n"
              "**Modes:**\n"
              "• **INSERT** (green) — Every scan adds stock (Stock In)\n"
              "• **TAKEOUT** (red) — Every scan removes stock (Stock Out)\n"
              "• **IDLE** (grey) — Scanning is paused\n\n"
              "**Workflow:**\n"
              "1. Tap the mode button to switch to INSERT or TAKEOUT\n"
              "2. Scan items — each scan adds a row to the **pending table**\n"
              "3. The pending table shows: item name, barcode, quantity (editable), predicted stock after\n"
              "4. You can edit quantities or remove items before confirming\n"
              "5. Click **Confirm** to apply all pending operations at once\n"
              "6. Click **Cancel** to discard the entire session\n\n"
              "**Bottom counter:** Shows \"X items, Y units pending\" in real time.\n\n"
              "**Recent sessions:** A collapsible section at the bottom shows the last 10 scanning "
              "sessions with summaries.\n\n"
              "**Tip:** Quick Scan is ideal for receiving shipments (INSERT mode) or processing "
              "customer orders (TAKEOUT mode).",
        "DE": "**Schnellscan** ist für schnelle barcode-gesteuerte Massenoperationen mit einem USB- oder "
              "Bluetooth-Barcode-Scanner konzipiert.\n\n"
              "**Modi:**\n"
              "• **EINBUCHEN** (grün) — Jeder Scan bucht Bestand ein\n"
              "• **AUSBUCHEN** (rot) — Jeder Scan bucht Bestand aus\n"
              "• **LEERLAUF** (grau) — Scannen pausiert\n\n"
              "**Arbeitsablauf:**\n"
              "1. Tippen Sie auf den Modus-Button um auf EINBUCHEN oder AUSBUCHEN zu wechseln\n"
              "2. Scannen Sie Artikel — jeder Scan fügt eine Zeile zur ausstehenden Tabelle hinzu\n"
              "3. Mengen bearbeiten oder Artikel entfernen vor dem Bestätigen\n"
              "4. **Bestätigen** um alle ausstehenden Operationen anzuwenden\n"
              "5. **Abbrechen** um die Sitzung zu verwerfen",
        "AR": "**المسح السريع** مصمم لعمليات الدُفعات السريعة القائمة على الباركود.\n\n"
              "**الأوضاع:**\n"
              "• **إدخال** (أخضر) — كل مسح يضيف مخزوناً\n"
              "• **إخراج** (أحمر) — كل مسح يزيل مخزوناً\n"
              "• **خمول** (رمادي) — المسح متوقف مؤقتاً\n\n"
              "**سير العمل:**\n"
              "1. اضغط على زر الوضع للتبديل\n"
              "2. امسح العناصر — كل مسح يضيف صفاً إلى الجدول المعلق\n"
              "3. يمكنك تعديل الكميات أو إزالة العناصر قبل التأكيد\n"
              "4. انقر **تأكيد** لتطبيق جميع العمليات المعلقة\n"
              "5. انقر **إلغاء** لتجاهل الجلسة بأكملها",
    },
    # ── Help: Reports ───────────────────────────────────────────────────────
    "help_reports": {
        "EN": "Reports & PDF Generation",
        "DE": "Berichte & PDF-Erstellung",
        "AR": "التقارير وإنشاء PDF",
    },
    "help_reports_body": {
        "EN": "The **Reports** page lets you generate printable PDF reports. Click any report card "
              "to start generation.\n\n"
              "**Available reports:**\n"
              "• **Inventory Report** — Complete stock levels for all items, grouped by category\n"
              "• **Low Stock Report** — Items below their minimum threshold, for procurement planning\n"
              "• **Transactions Report** — Full audit trail of all stock movements with dates and notes\n"
              "• **Summary Report** — KPI cards (total items, value, health) plus category charts\n"
              "• **Audit Sheet** — Blank printable form for physical inventory counts. "
              "Has columns for Actual count, Difference, and Notes with a sign-off area at the bottom\n"
              "• **Barcode Labels** — PDF sheet with scannable barcode labels for all items that have barcodes\n\n"
              "**How it works:**\n"
              "1. Click a report card\n"
              "2. A background worker generates the PDF (status bar shows progress)\n"
              "3. When ready, click **Open** to view, print, or save the PDF",
        "DE": "Die **Berichte**-Seite ermöglicht das Erstellen druckbarer PDF-Berichte.\n\n"
              "**Verfügbare Berichte:**\n"
              "• **Inventarbericht** — Vollständige Bestandsübersicht nach Kategorie\n"
              "• **Niedriger Bestand** — Artikel unter Mindestbestand, für Nachbestellung\n"
              "• **Transaktionsbericht** — Vollständiges Protokoll aller Bestandsbewegungen\n"
              "• **Zusammenfassung** — KPI-Karten plus Kategorien-Diagramme\n"
              "• **Inventurbogen** — Druckbares Formular für physische Inventur\n"
              "• **Barcode-Etiketten** — PDF mit scannbaren Barcode-Etiketten\n\n"
              "**Ablauf:** Karte anklicken → PDF wird im Hintergrund generiert → Öffnen zum Anzeigen/Drucken",
        "AR": "صفحة **التقارير** تتيح لك إنشاء تقارير PDF قابلة للطباعة.\n\n"
              "**التقارير المتاحة:**\n"
              "• **تقرير المخزون** — مستويات المخزون الكاملة مجمعة حسب الفئة\n"
              "• **تقرير المخزون المنخفض** — العناصر تحت الحد الأدنى\n"
              "• **تقرير المعاملات** — سجل كامل لجميع حركات المخزون\n"
              "• **تقرير ملخص** — بطاقات مؤشرات الأداء مع رسوم بيانية\n"
              "• **ورقة الجرد** — نموذج فارغ قابل للطباعة للعد الفعلي\n"
              "• **ملصقات الباركود** — ورقة PDF بملصقات باركود قابلة للمسح",
    },
    # ── Help: Analytics ─────────────────────────────────────────────────────
    "help_analytics": {
        "EN": "Analytics Dashboard",
        "DE": "Analyse-Dashboard",
        "AR": "لوحة التحليلات",
    },
    "help_analytics_body": {
        "EN": "The **Analytics** page is the app's home screen, showing an at-a-glance overview of "
              "your inventory health.\n\n"
              "**KPI cards (top row):**\n"
              "• **Total Items** — Count of all distinct products/parts in your inventory\n"
              "• **Units in Stock** — Total quantity across all items\n"
              "• **Inventory Value** — Sum of (quantity × sell price) for all items\n"
              "• **Stock Health** — Percentage of items at or above their minimum threshold\n\n"
              "**Charts:**\n"
              "• **Stock Health Donut** — Segments for OK (green), Low (yellow), Out of Stock (red)\n"
              "• **Category Distribution** — Horizontal bar chart showing unit counts per category\n"
              "• **Transaction Trend** — 30-day line graph of daily Stock-In vs Stock-Out volume\n\n"
              "The dashboard auto-refreshes when you navigate to it.",
        "DE": "Die **Analyse**-Seite ist der Startbildschirm mit einer Übersicht über Ihre Bestandsgesundheit.\n\n"
              "**KPI-Karten:**\n"
              "• **Gesamtartikel** — Anzahl aller Produkte/Teile\n"
              "• **Einheiten auf Lager** — Gesamtmenge aller Artikel\n"
              "• **Inventarwert** — Summe von (Menge × Verkaufspreis)\n"
              "• **Bestandsgesundheit** — Prozentsatz der Artikel über Mindestbestand\n\n"
              "**Diagramme:**\n"
              "• **Bestandsgesundheit** — Donut: OK, Niedrig, Ausverkauft\n"
              "• **Kategorieverteilung** — Balkendiagramm pro Kategorie\n"
              "• **Transaktionstrend** — 30-Tage-Liniengrafik Ein-/Ausbuchungen",
        "AR": "صفحة **التحليلات** هي الشاشة الرئيسية التي تعرض نظرة سريعة على صحة مخزونك.\n\n"
              "**بطاقات مؤشرات الأداء:**\n"
              "• **إجمالي العناصر** — عدد جميع المنتجات/القطع\n"
              "• **الوحدات في المخزون** — الكمية الإجمالية لجميع العناصر\n"
              "• **قيمة المخزون** — مجموع (الكمية × سعر البيع)\n"
              "• **صحة المخزون** — نسبة العناصر فوق الحد الأدنى\n\n"
              "**الرسوم البيانية:**\n"
              "• **صحة المخزون** — دائري: جيد، منخفض، نفد\n"
              "• **توزيع الفئات** — مخطط شريطي لكل فئة\n"
              "• **اتجاه المعاملات** — رسم بياني خطي لـ 30 يوماً",
    },
    # ── Help: Barcode Generator ─────────────────────────────────────────────
    "help_barcode_gen": {
        "EN": "Barcode Generator",
        "DE": "Barcode-Generator",
        "AR": "مولد الباركود",
    },
    "help_barcode_gen_body": {
        "EN": "The **Barcode Generator** creates printable barcode label sheets in PDF format.\n\n"
              "**Scope selection (left panel):**\n"
              "• **All** — Generate labels for your entire inventory\n"
              "• **Category** — Pick one category, generate for all its items\n"
              "• **Model** — Select specific phone models\n"
              "• **Part Type** — Select specific part types\n\n"
              "**Options:**\n"
              "• Barcode format: Code39 or Code128\n"
              "• Include command barcodes (SKU lookup codes)\n"
              "• Include existing barcodes (for items that already have one assigned)\n\n"
              "**Output:**\n"
              "Click **Generate** to create the PDF. Use the preview on the right to browse pages, "
              "then **Download** or **Print** directly.",
        "DE": "Der **Barcode-Generator** erstellt druckbare Barcode-Etiketten im PDF-Format.\n\n"
              "**Bereichsauswahl:**\n"
              "• **Alle** — Etiketten für gesamtes Inventar\n"
              "• **Kategorie** — Eine Kategorie auswählen\n"
              "• **Modell** — Bestimmte Telefonmodelle\n"
              "• **Teiletyp** — Bestimmte Teiletypen\n\n"
              "**Ausgabe:** Generieren → Vorschau → Herunterladen oder Drucken",
        "AR": "**مولد الباركود** ينشئ أوراق ملصقات باركود قابلة للطباعة بصيغة PDF.\n\n"
              "**اختيار النطاق:**\n"
              "• **الكل** — إنشاء ملصقات لكامل المخزون\n"
              "• **الفئة** — اختيار فئة واحدة\n"
              "• **الموديل** — اختيار موديلات محددة\n"
              "• **نوع القطعة** — اختيار أنواع قطع محددة\n\n"
              "**النتيجة:** انقر إنشاء → معاينة → تحميل أو طباعة",
    },
    # ── Help: Transactions ──────────────────────────────────────────────────
    "help_transactions": {
        "EN": "Transaction History",
        "DE": "Transaktionsverlauf",
        "AR": "سجل المعاملات",
    },
    "help_transactions_body": {
        "EN": "The **Transactions** page is your complete audit trail. Every stock-in, stock-out, "
              "and adjustment is permanently recorded here.\n\n"
              "**Table columns:** Timestamp, Item Name, Operation (IN/OUT/ADJUST), Quantity, "
              "Stock Before, Stock After, Note\n\n"
              "**Filters:**\n"
              "• **Date range** — Pick start and end dates\n"
              "• **Operation type** — Filter by IN, OUT, or ADJUST\n"
              "• **Search** — Find by item name or barcode\n\n"
              "**Export:** Click the export button to save filtered results as a CSV file for "
              "accounting or external reporting.\n\n"
              "**Tip:** This page is useful for investigating discrepancies — you can trace exactly "
              "when stock changed, by how much, and any notes that were added.",
        "DE": "Die **Transaktionen**-Seite ist Ihr vollständiger Protokollverlauf.\n\n"
              "**Tabellenspalten:** Zeitstempel, Artikelname, Operation, Menge, Bestand vorher/nachher, Notiz\n\n"
              "**Filter:** Datumsbereich, Operationstyp, Suche\n\n"
              "**Export:** Gefilterte Ergebnisse als CSV-Datei speichern.",
        "AR": "صفحة **المعاملات** هي سجل التدقيق الكامل الخاص بك.\n\n"
              "**أعمدة الجدول:** الطابع الزمني، اسم العنصر، العملية، الكمية، المخزون قبل/بعد، ملاحظة\n\n"
              "**الفلاتر:** نطاق التاريخ، نوع العملية، البحث\n\n"
              "**التصدير:** حفظ النتائج المفلترة كملف CSV.",
    },
    # ── Help: Admin Settings ────────────────────────────────────────────────
    "help_admin": {
        "EN": "Admin Settings",
        "DE": "Admin-Einstellungen",
        "AR": "إعدادات المسؤول",
    },
    "help_admin_body": {
        "EN": "Access the Admin panel from the gear icon in the top-right corner of the header bar. "
              "If a PIN is set, you will need to enter it first.\n\n"
              "**Tab 1 — Shop Settings:**\n"
              "Shop name, logo, currency (symbol and position), language (EN/DE/AR), "
              "theme selection (Pro Dark, Pro Light, Dark, Light), admin PIN, contact info.\n\n"
              "**Tab 2 — Categories:**\n"
              "Add, edit, delete, and reorder inventory categories. "
              "Each category has a name in all 3 languages and an optional icon.\n\n"
              "**Tab 3 — Part Types:**\n"
              "Manage part types within categories. Assign colours, reorder, delete (only if stock is zero).\n\n"
              "**Tab 4 — Models:**\n"
              "Add or remove phone models (brand + name). Cannot delete models with stock > 0.\n\n"
              "**Tab 5 — Scan Settings:**\n"
              "Configure barcode scanner timeout and session behaviour.\n\n"
              "**Tab 6 — Backup & Restore:**\n"
              "Create database snapshots, view backup list, restore from any previous backup, "
              "delete old backups.\n\n"
              "**Tab 7 — Import/Export:**\n"
              "Export inventory, transactions, or low-stock data as CSV or Excel. "
              "Import products from CSV/Excel with column mapping and duplicate handling.\n\n"
              "**Tab 8 — Database Tools:**\n"
              "Optimise (VACUUM + PRAGMA optimize), integrity check, and compact the database.",
        "DE": "Zugriff über das Zahnrad-Symbol oben rechts. Bei gesetzter PIN muss diese zuerst eingegeben werden.\n\n"
              "**Tab 1 — Shop:** Name, Logo, Währung, Sprache, Theme, PIN, Kontakt\n"
              "**Tab 2 — Kategorien:** Erstellen, bearbeiten, löschen, umsortieren\n"
              "**Tab 3 — Teiletypen:** Innerhalb von Kategorien verwalten, Farben zuweisen\n"
              "**Tab 4 — Modelle:** Telefonmodelle hinzufügen/entfernen\n"
              "**Tab 5 — Scan:** Barcode-Scanner-Einstellungen\n"
              "**Tab 6 — Backup:** Datenbank-Sicherungen erstellen/wiederherstellen\n"
              "**Tab 7 — Import/Export:** CSV/Excel ein- und ausgeben\n"
              "**Tab 8 — Datenbank:** Optimieren, Integritätsprüfung, Komprimieren",
        "AR": "الوصول من أيقونة الترس في الزاوية العلوية. إذا تم تعيين رمز PIN يجب إدخاله أولاً.\n\n"
              "**علامة 1 — المتجر:** الاسم، الشعار، العملة، اللغة، السمة، PIN، معلومات الاتصال\n"
              "**علامة 2 — الفئات:** إنشاء وتعديل وحذف وإعادة ترتيب\n"
              "**علامة 3 — أنواع القطع:** إدارة داخل الفئات، تعيين الألوان\n"
              "**علامة 4 — الموديلات:** إضافة/إزالة موديلات الهواتف\n"
              "**علامة 5 — المسح:** إعدادات ماسح الباركود\n"
              "**علامة 6 — النسخ الاحتياطي:** إنشاء/استعادة نسخ احتياطية\n"
              "**علامة 7 — استيراد/تصدير:** CSV/Excel استيراد وتصدير\n"
              "**علامة 8 — قاعدة البيانات:** تحسين، فحص السلامة، ضغط",
    },
    # ── Help: Import/Export ─────────────────────────────────────────────────
    "help_import_export": {
        "EN": "Import & Export",
        "DE": "Import & Export",
        "AR": "الاستيراد والتصدير",
    },
    "help_import_export_body": {
        "EN": "**Exporting data (Admin → Import/Export):**\n"
              "• **Inventory CSV** — All items with brand, name, colour, stock, price, barcode\n"
              "• **Transactions CSV** — Historical record of all stock movements\n"
              "• **Low Stock CSV** — Only items below their minimum threshold\n"
              "• **Excel Workbook** — Multi-sheet XLSX with inventory and summaries\n\n"
              "**Importing products:**\n"
              "1. Click **Import** and select a CSV or XLSX file\n"
              "2. A **preview table** shows the first rows of your file\n"
              "3. **Map columns** — For each required field (brand, name, stock, price), "
              "select which column in your file matches\n"
              "4. Choose how to handle duplicates: skip or update existing\n"
              "5. Click **Import** to commit\n\n"
              "**Supported formats:** .csv and .xlsx (Excel)\n\n"
              "**Common workflow:** Export → edit in a spreadsheet program → re-import to update your data.",
        "DE": "**Daten exportieren (Admin → Import/Export):**\n"
              "• **Inventar CSV** — Alle Artikel mit Daten\n"
              "• **Transaktionen CSV** — Historische Bestandsbewegungen\n"
              "• **Niedriger Bestand CSV** — Nur Artikel unter Mindestbestand\n"
              "• **Excel** — Mehrseitige XLSX-Arbeitsmappe\n\n"
              "**Produkte importieren:** Datei wählen → Vorschau → Spalten zuordnen → Importieren",
        "AR": "**تصدير البيانات (المسؤول → استيراد/تصدير):**\n"
              "• **CSV المخزون** — جميع العناصر مع البيانات\n"
              "• **CSV المعاملات** — سجل تاريخي لحركات المخزون\n"
              "• **CSV المخزون المنخفض** — العناصر تحت الحد الأدنى فقط\n"
              "• **Excel** — مصنف XLSX متعدد الأوراق\n\n"
              "**استيراد المنتجات:** اختر ملف → معاينة → تعيين الأعمدة → استيراد",
    },
    # ── Help: Backup & Restore ──────────────────────────────────────────────
    "help_backup": {
        "EN": "Backup & Restore",
        "DE": "Sicherung & Wiederherstellung",
        "AR": "النسخ الاحتياطي والاستعادة",
    },
    "help_backup_body": {
        "EN": "**Creating a backup (Admin → Backup):**\n"
              "Click **Create Backup** to take a snapshot of your entire database. "
              "Backups are saved with a timestamp in the filename.\n\n"
              "**Backup list:** Shows all existing backups with date, file size, and filename.\n\n"
              "**Restoring:** Select a backup from the list and click **Restore**. "
              "This will replace your current database with the selected backup. "
              "**Warning:** Restoring overwrites all current data!\n\n"
              "**Deleting old backups:** Select a backup and click **Delete** to free up disk space.\n\n"
              "**Tip:** Create a backup before making major changes like bulk imports, "
              "bulk price updates, or category restructuring.",
        "DE": "**Sicherung erstellen (Admin → Backup):** Klick auf **Sicherung erstellen** für einen "
              "Snapshot der gesamten Datenbank.\n\n"
              "**Wiederherstellen:** Sicherung auswählen und **Wiederherstellen** klicken. "
              "**Achtung:** Die aktuelle Datenbank wird überschrieben!\n\n"
              "**Tipp:** Erstellen Sie vor großen Änderungen immer eine Sicherung.",
        "AR": "**إنشاء نسخة احتياطية (المسؤول → النسخ الاحتياطي):** انقر **إنشاء نسخة** لأخذ لقطة من قاعدة البيانات.\n\n"
              "**الاستعادة:** حدد نسخة وانقر **استعادة**. **تحذير:** سيتم استبدال جميع البيانات الحالية!\n\n"
              "**نصيحة:** أنشئ نسخة احتياطية قبل إجراء تغييرات كبيرة.",
    },
    # ── Help: Inventory Page ────────────────────────────────────────────────
    "help_inventory_page": {
        "EN": "Inventory Page",
        "DE": "Inventar-Seite",
        "AR": "صفحة المخزون",
    },
    "help_inventory_page_body": {
        "EN": "The **Inventory** page is your main workspace for standalone products "
              "(items not in the category matrix).\n\n"
              "**Layout (3 areas):**\n"
              "• **Top** — Mini dashboard with KPI cards: total items, units, value, health %\n"
              "• **Left (70%)** — Product table with columns: Name, Barcode, Stock, Price, Status\n"
              "• **Right (30%)** — Detail panel for the selected product\n\n"
              "**Search & filters:**\n"
              "• **Search bar** — Type to filter by brand, name, colour, or barcode\n"
              "• **Status filter** — Show All, In Stock, Low Stock, or Out of Stock\n"
              "• **Advanced Filters** — Click the toggle button to expand:\n"
              "  – Category dropdown (All, Products Only, or a specific category)\n"
              "  – Price range (min/max)\n\n"
              "**Actions on a selected product (detail panel):**\n"
              "• Stock In (↑), Stock Out (↓), Adjust (⇅)\n"
              "• Edit product details\n"
              "• Delete product\n"
              "• View barcode preview\n"
              "• View product image (if attached)\n\n"
              "**Adding a product:** Use the + button in the header or Ctrl+N.\n"
              "**Bulk price update:** Select multiple products, right-click → Bulk Price Update.",
        "DE": "Die **Inventar**-Seite ist Ihr Hauptarbeitsbereich für eigenständige Produkte.\n\n"
              "**Aufbau:**\n"
              "• **Oben** — Mini-Dashboard mit KPI-Karten\n"
              "• **Links** — Produkttabelle mit Spalten: Name, Barcode, Bestand, Preis, Status\n"
              "• **Rechts** — Detailpanel für das ausgewählte Produkt\n\n"
              "**Suche & Filter:** Suchleiste, Statusfilter, erweiterte Filter (Kategorie, Preisspanne)\n\n"
              "**Aktionen:** Ein-/Ausbuchen, Bearbeiten, Löschen, Barcode-Vorschau, Produktbild\n\n"
              "**Hinzufügen:** + Button oder Strg+N. **Massenpreis:** Mehrere auswählen → Rechtsklick.",
        "AR": "صفحة **المخزون** هي مساحة عملك الرئيسية للمنتجات المستقلة.\n\n"
              "**التخطيط:**\n"
              "• **أعلى** — لوحة مصغرة مع بطاقات مؤشرات الأداء\n"
              "• **يسار** — جدول المنتجات: الاسم، الباركود، المخزون، السعر، الحالة\n"
              "• **يمين** — لوحة تفاصيل المنتج المحدد\n\n"
              "**البحث والفلاتر:** شريط البحث، فلتر الحالة، فلاتر متقدمة (الفئة، نطاق السعر)\n\n"
              "**الإجراءات:** إدخال/إخراج، تعديل، حذف، معاينة الباركود، صورة المنتج",
    },
    # ── Help: Product Images ────────────────────────────────────────────────
    "help_product_images": {
        "EN": "Product Images",
        "DE": "Produktbilder",
        "AR": "صور المنتجات",
    },
    "help_product_images_body": {
        "EN": "You can attach a photo to any standalone product for easy visual identification.\n\n"
              "**Adding an image:**\n"
              "1. Open the Add Product or Edit Product dialog\n"
              "2. In the Identity section, click **Browse…** next to the Image field\n"
              "3. Select a JPG, PNG, WEBP, or BMP file from your computer\n"
              "4. A thumbnail preview appears in the dialog\n"
              "5. Save the product — the image is stored alongside your database\n\n"
              "**Removing an image:** Click **Remove** next to the preview in the edit dialog.\n\n"
              "**Where images appear:**\n"
              "• In the **detail panel** on the Inventory page (150px thumbnail)\n"
              "• In the **edit dialog** as a 64px preview\n\n"
              "**Image handling:** Images are automatically resized to max 800×800 pixels to save "
              "disk space. Supported formats: JPG, JPEG, PNG, WEBP, BMP.",
        "DE": "Sie können jedem eigenständigen Produkt ein Foto anhängen.\n\n"
              "**Bild hinzufügen:**\n"
              "1. Öffnen Sie den Produkt-Dialog (Hinzufügen oder Bearbeiten)\n"
              "2. Klicken Sie auf **Durchsuchen…** neben dem Bildfeld\n"
              "3. Wählen Sie eine JPG-, PNG-, WEBP- oder BMP-Datei\n"
              "4. Eine Vorschau erscheint im Dialog\n"
              "5. Produkt speichern — das Bild wird neben der Datenbank gespeichert\n\n"
              "**Bild entfernen:** Klicken Sie auf **Entfernen** im Bearbeitungsdialog.\n\n"
              "**Bilder werden automatisch auf max. 800×800 Pixel verkleinert.",
        "AR": "يمكنك إرفاق صورة بأي منتج مستقل للتعرف البصري السهل.\n\n"
              "**إضافة صورة:**\n"
              "1. افتح نافذة إضافة أو تعديل المنتج\n"
              "2. انقر **استعراض…** بجوار حقل الصورة\n"
              "3. اختر ملف JPG أو PNG أو WEBP أو BMP\n"
              "4. تظهر معاينة مصغرة في النافذة\n"
              "5. احفظ المنتج — يتم تخزين الصورة بجوار قاعدة البيانات\n\n"
              "**إزالة صورة:** انقر **إزالة** في نافذة التعديل.\n\n"
              "**يتم تغيير حجم الصور تلقائياً إلى 800×800 بكسل كحد أقصى.",
    },
    "filter_status_in_stock": {
        "EN": "In Stock",
        "DE": "Auf Lager",
        "AR": "متوفر",
    },
    "filter_status_low_stock": {
        "EN": "Low Stock",
        "DE": "Niedriger Bestand",
        "AR": "مخزون منخفض",
    },
    "filter_status_critical": {
        "EN": "Critical",
        "DE": "Kritisch",
        "AR": "حرج",
    },
    "filter_status_out_of_stock": {
        "EN": "Out of Stock",
        "DE": "Nicht vorrätig",
        "AR": "نفد المخزون",
    },
    "filter_sort_name_asc": {
        "EN": "Name (A→Z)",
        "DE": "Name (A→Z)",
        "AR": "الاسم (أ→ي)",
    },
    "filter_sort_name_desc": {
        "EN": "Name (Z→A)",
        "DE": "Name (Z→A)",
        "AR": "الاسم (ي→أ)",
    },
    "filter_sort_stock_asc": {
        "EN": "Stock (Low→High)",
        "DE": "Bestand (Niedrig→Hoch)",
        "AR": "المخزون (منخفض→مرتفع)",
    },
    "filter_sort_stock_desc": {
        "EN": "Stock (High→Low)",
        "DE": "Bestand (Hoch→Niedrig)",
        "AR": "المخزون (مرتفع→منخفض)",
    },
    "filter_sort_price_asc": {
        "EN": "Price (Low→High)",
        "DE": "Preis (Niedrig→Hoch)",
        "AR": "السعر (منخفض→مرتفع)",
    },
    "filter_sort_price_desc": {
        "EN": "Price (High→Low)",
        "DE": "Preis (Hoch→Niedrig)",
        "AR": "السعر (مرتفع→منخفض)",
    },
    "filter_sort_updated_desc": {
        "EN": "Recently Updated",
        "DE": "Kürzlich aktualisiert",
        "AR": "آخر تحديث",
    },
    "filter_active": {
        "EN": "{n} filter(s) active",
        "DE": "{n} Filter aktiv",
        "AR": "{n} فلتر نشط",
    },
    # ── Reports ───────────────────────────────────────────────────────────────────
    "report_inventory_title": {
        "EN": "Inventory Report",
        "DE": "Inventarbericht",
        "AR": "تقرير المخزون",
    },
    "report_low_stock_title": {
        "EN": "Low Stock Report",
        "DE": "Niedriger Bestand Bericht",
        "AR": "تقرير المخزون المنخفض",
    },
    "report_txn_title": {
        "EN": "Transaction Report",
        "DE": "Transaktionsbericht",
        "AR": "تقرير المعاملات",
    },
    "report_summary_title": {
        "EN": "Summary Report",
        "DE": "Zusammenfassungsbericht",
        "AR": "تقرير موجز",
    },
    "report_generated_at": {
        "EN": "Generated: {date}",
        "DE": "Erzeugt: {date}",
        "AR": "تم الإنشاء: {date}",
    },
    "report_page": {
        "EN": "Page {current} of {total}",
        "DE": "Seite {current} von {total}",
        "AR": "الصفحة {current} من {total}",
    },
    "status_exported": {
        "EN": "Report exported: {path}",
        "DE": "Bericht exportiert: {path}",
        "AR": "تم تصدير التقرير: {path}",
    },
    "msg_export_title": {
        "EN": "Export Successful",
        "DE": "Export erfolgreich",
        "AR": "نجح التصدير",
    },
    "msg_export_body": {
        "EN": "Report saved to:\n{path}",
        "DE": "Bericht gespeichert unter:\n{path}",
        "AR": "تم حفظ التقرير في:\n{path}",
    },
    "msg_export_failed": {
        "EN": "Export Failed",
        "DE": "Export fehlgeschlagen",
        "AR": "فشل التصدير",
    },
    "msg_no_low_stock_items": {
        "EN": "No items with low stock",
        "DE": "Keine Artikel mit niedrigem Bestand",
        "AR": "لا توجد عناصر بمخزون منخفض",
    },

    # ── Phase 1: Hardcoded string fixes ──────────────────────────────────────
    "tooltip_toggle_sidebar": {
        "EN": "Toggle sidebar",
        "DE": "Seitenleiste umschalten",
        "AR": "تبديل الشريط الجانبي",
    },
    "cat_new_category": {
        "EN": "New Category",
        "DE": "Neue Kategorie",
        "AR": "فئة جديدة",
    },
    "icon_change_icon": {
        "EN": "Change Icon…",
        "DE": "Symbol ändern…",
        "AR": "تغيير الأيقونة…",
    },
    "icon_selected": {
        "EN": "Selected:  {icon}",
        "DE": "Ausgewählt:  {icon}",
        "AR": "المحدد:  {icon}",
    },
    "btn_ok": {
        "EN": "OK",
        "DE": "OK",
        "AR": "موافق",
    },
    "db_tools_operations": {
        "EN": "Operations",
        "DE": "Operationen",
        "AR": "العمليات",
    },
    "db_tools_running_optimizer": {
        "EN": "Running optimizer...",
        "DE": "Optimierung läuft...",
        "AR": "جاري التحسين...",
    },
    "db_tools_optimizing": {
        "EN": "Optimizing...",
        "DE": "Optimierung...",
        "AR": "جاري التحسين...",
    },
    "db_tools_complete": {
        "EN": "Complete",
        "DE": "Abgeschlossen",
        "AR": "مكتمل",
    },
    "db_tools_checking_integrity": {
        "EN": "Checking integrity...",
        "DE": "Integrität prüfen...",
        "AR": "جاري فحص السلامة...",
    },
    "db_tools_integrity_issues": {
        "EN": "Integrity issues found:\n{msg}",
        "DE": "Integritätsprobleme gefunden:\n{msg}",
        "AR": "تم العثور على مشاكل في السلامة:\n{msg}",
    },
    "db_tools_compacting": {
        "EN": "Compacting database...",
        "DE": "Datenbank komprimieren...",
        "AR": "جاري ضغط قاعدة البيانات...",
    },
    "db_tools_unknown": {
        "EN": "Unknown",
        "DE": "Unbekannt",
        "AR": "غير معروف",
    },
    "db_tools_tables": {
        "EN": "Tables:",
        "DE": "Tabellen:",
        "AR": "الجداول:",
    },
    "db_tools_total_rows": {
        "EN": "Total Rows:",
        "DE": "Gesamtzeilen:",
        "AR": "إجمالي الصفوف:",
    },
    "db_tools_error_loading": {
        "EN": "Error loading database info: {err}",
        "DE": "Fehler beim Laden der Datenbankinfo: {err}",
        "AR": "خطأ في تحميل معلومات قاعدة البيانات: {err}",
    },
    "db_tools_confirm_optimize": {
        "EN": "This will optimize the database and may take a moment. Continue?",
        "DE": "Die Datenbank wird optimiert, dies kann einen Moment dauern. Fortfahren?",
        "AR": "سيتم تحسين قاعدة البيانات وقد يستغرق ذلك بعض الوقت. متابعة؟",
    },
    "db_tools_success": {
        "EN": "Success",
        "DE": "Erfolg",
        "AR": "نجاح",
    },
    "db_tools_error": {
        "EN": "Error",
        "DE": "Fehler",
        "AR": "خطأ",
    },
    "wizard_shop_name_ph": {
        "EN": "e.g. My Shop",
        "DE": "z.B. Mein Laden",
        "AR": "مثال: متجري",
    },
    "wizard_default_name": {
        "EN": "Stock Manager Pro",
        "DE": "Stock Manager Pro",
        "AR": "Stock Manager Pro",
    },

    # ── Phase 2: Transactions Page ──────────────────────────────────────────
    "txn_page_title": {
        "EN": "Transaction History",
        "DE": "Transaktionsverlauf",
        "AR": "سجل المعاملات",
    },
    "txn_filter_all_ops": {
        "EN": "All Operations",
        "DE": "Alle Vorgänge",
        "AR": "جميع العمليات",
    },
    "txn_filter_in": {
        "EN": "Stock In",
        "DE": "Eingang",
        "AR": "إدخال",
    },
    "txn_filter_out": {
        "EN": "Stock Out",
        "DE": "Ausgang",
        "AR": "إخراج",
    },
    "txn_filter_adjust": {
        "EN": "Adjustments",
        "DE": "Korrekturen",
        "AR": "تعديلات",
    },
    "txn_filter_create": {
        "EN": "Created",
        "DE": "Erstellt",
        "AR": "إنشاء",
    },
    "txn_date_from": {
        "EN": "From",
        "DE": "Von",
        "AR": "من",
    },
    "txn_date_to": {
        "EN": "To",
        "DE": "Bis",
        "AR": "إلى",
    },
    "txn_search_ph": {
        "EN": "Search transactions…",
        "DE": "Transaktionen suchen…",
        "AR": "بحث في المعاملات…",
    },
    "txn_summary_total": {
        "EN": "{n} transactions",
        "DE": "{n} Transaktionen",
        "AR": "{n} معاملة",
    },
    "txn_summary_in": {
        "EN": "In: +{n}",
        "DE": "Eingang: +{n}",
        "AR": "إدخال: +{n}",
    },
    "txn_summary_out": {
        "EN": "Out: -{n}",
        "DE": "Ausgang: -{n}",
        "AR": "إخراج: -{n}",
    },
    "txn_summary_net": {
        "EN": "Net: {n}",
        "DE": "Netto: {n}",
        "AR": "الصافي: {n}",
    },
    "txn_export": {
        "EN": "Export",
        "DE": "Exportieren",
        "AR": "تصدير",
    },
    "txn_showing": {
        "EN": "Showing {shown} of {total}",
        "DE": "Zeige {shown} von {total}",
        "AR": "عرض {shown} من {total}",
    },
    "txn_load_more": {
        "EN": "Load More",
        "DE": "Mehr laden",
        "AR": "تحميل المزيد",
    },

    # ── Phase 2: Reports Page ───────────────────────────────────────────────
    "nav_reports": {
        "EN": "Reports",
        "DE": "Berichte",
        "AR": "التقارير",
    },
    "reports_title": {
        "EN": "Reports",
        "DE": "Berichte",
        "AR": "التقارير",
    },
    "report_type_inventory": {
        "EN": "Full Inventory Report",
        "DE": "Vollständiger Bestandsbericht",
        "AR": "تقرير المخزون الكامل",
    },
    "report_type_inventory_desc": {
        "EN": "Complete list of all products with stock levels, prices, and status.",
        "DE": "Vollständige Liste aller Produkte mit Bestand, Preisen und Status.",
        "AR": "قائمة كاملة بجميع المنتجات مع مستويات المخزون والأسعار والحالة.",
    },
    "report_type_low_stock": {
        "EN": "Low Stock Report",
        "DE": "Niedrigbestand-Bericht",
        "AR": "تقرير المخزون المنخفض",
    },
    "report_type_low_stock_desc": {
        "EN": "Items below minimum stock threshold, sorted by urgency.",
        "DE": "Artikel unter dem Mindestbestand, sortiert nach Dringlichkeit.",
        "AR": "العناصر التي تقل عن الحد الأدنى للمخزون، مرتبة حسب الأولوية.",
    },
    "report_type_transactions": {
        "EN": "Transaction Report",
        "DE": "Transaktionsbericht",
        "AR": "تقرير المعاملات",
    },
    "report_type_transactions_desc": {
        "EN": "Stock movements over the last 30 days.",
        "DE": "Bestandsbewegungen der letzten 30 Tage.",
        "AR": "حركات المخزون خلال آخر 30 يومًا.",
    },
    "report_type_summary": {
        "EN": "Executive Summary",
        "DE": "Zusammenfassung",
        "AR": "ملخص تنفيذي",
    },
    "report_type_summary_desc": {
        "EN": "One-page overview with key metrics and insights.",
        "DE": "Einseitige Übersicht mit Kennzahlen und Erkenntnissen.",
        "AR": "نظرة عامة من صفحة واحدة مع المقاييس والرؤى الرئيسية.",
    },
    "report_type_audit": {
        "EN": "Inventory Audit",
        "DE": "Inventur-Zählung",
        "AR": "جرد المخزون",
    },
    "report_type_audit_desc": {
        "EN": "Print-ready sheet for physical stock counts with columns for actual vs. system.",
        "DE": "Druckfertiges Blatt für physische Bestandszählung mit Ist- und Soll-Spalten.",
        "AR": "ورقة جاهزة للطباعة لجرد المخزون الفعلي مع أعمدة للفعلي مقابل النظام.",
    },
    "report_type_discrepancy": {
        "EN": "Discrepancy Report",
        "DE": "Abweichungsbericht",
        "AR": "تقرير التناقضات",
    },
    "report_type_discrepancy_desc": {
        "EN": "Variance analysis comparing expected vs. actual stock from audit data.",
        "DE": "Abweichungsanalyse: Vergleich von Soll- und Ist-Bestand aus Prüfungsdaten.",
        "AR": "تحليل التباين بمقارنة المخزون المتوقع مقابل الفعلي من بيانات الجرد.",
    },
    "report_type_barcode": {
        "EN": "Barcode Labels",
        "DE": "Barcode-Etiketten",
        "AR": "ملصقات الباركود",
    },
    "report_type_barcode_desc": {
        "EN": "Printable barcode label sheets for all items with assigned barcodes.",
        "DE": "Druckbare Barcode-Etikettenblätter für alle Artikel mit zugewiesenen Barcodes.",
        "AR": "أوراق ملصقات باركود قابلة للطباعة لجميع الأصناف ذات الباركود.",
    },
    "report_audit_title": {
        "EN": "Inventory Audit Sheet",
        "DE": "Inventur-Zählblatt",
        "AR": "ورقة جرد المخزون",
    },
    "report_discrepancy_title": {
        "EN": "Discrepancy Report",
        "DE": "Abweichungsbericht",
        "AR": "تقرير التناقضات",
    },
    "report_discrepancy_btn": {
        "EN": "Discrepancy Report",
        "DE": "Abweichungsbericht",
        "AR": "تقرير التناقضات",
    },
    "report_barcode_title": {
        "EN": "Barcode Label Sheet",
        "DE": "Barcode-Etikettenblatt",
        "AR": "ورقة ملصقات الباركود",
    },
    "report_generate": {
        "EN": "Generate Report",
        "DE": "Bericht erstellen",
        "AR": "إنشاء التقرير",
    },
    "report_generating": {
        "EN": "Generating…",
        "DE": "Wird erstellt…",
        "AR": "جاري الإنشاء…",
    },
    "report_open": {
        "EN": "Open PDF",
        "DE": "PDF öffnen",
        "AR": "فتح PDF",
    },
    "report_success": {
        "EN": "Report generated successfully!",
        "DE": "Bericht erfolgreich erstellt!",
        "AR": "تم إنشاء التقرير بنجاح!",
    },
    "report_error": {
        "EN": "Failed to generate report: {err}",
        "DE": "Bericht konnte nicht erstellt werden: {err}",
        "AR": "فشل إنشاء التقرير: {err}",
    },

    # ── Phase 2: Context Menus ──────────────────────────────────────────────
    "ctx_stock_in": {
        "EN": "Stock In…",
        "DE": "Eingang…",
        "AR": "إدخال مخزون…",
    },
    "ctx_stock_out": {
        "EN": "Stock Out…",
        "DE": "Ausgang…",
        "AR": "إخراج مخزون…",
    },
    "ctx_adjust": {
        "EN": "Adjust Stock…",
        "DE": "Bestand korrigieren…",
        "AR": "تعديل المخزون…",
    },
    "ctx_edit": {
        "EN": "Edit Product…",
        "DE": "Produkt bearbeiten…",
        "AR": "تعديل المنتج…",
    },
    "ctx_delete": {
        "EN": "Delete Product",
        "DE": "Produkt löschen",
        "AR": "حذف المنتج",
    },
    "ctx_copy_barcode": {
        "EN": "Copy Barcode",
        "DE": "Barcode kopieren",
        "AR": "نسخ الباركود",
    },
    "ctx_copy_name": {
        "EN": "Copy Name",
        "DE": "Name kopieren",
        "AR": "نسخ الاسم",
    },
    "ctx_view_txns": {
        "EN": "View Transactions",
        "DE": "Transaktionen anzeigen",
        "AR": "عرض المعاملات",
    },
    "ctx_select_all": {
        "EN": "Select All",
        "DE": "Alle auswählen",
        "AR": "تحديد الكل",
    },
    "ctx_bulk_in": {
        "EN": "Bulk Stock In…",
        "DE": "Massen-Eingang…",
        "AR": "إدخال مخزون مجمّع…",
    },
    "ctx_bulk_out": {
        "EN": "Bulk Stock Out…",
        "DE": "Massen-Ausgang…",
        "AR": "إخراج مخزون مجمّع…",
    },
    "ctx_bulk_delete": {
        "EN": "Delete Selected ({n})",
        "DE": "Ausgewählte löschen ({n})",
        "AR": "حذف المحدد ({n})",
    },
    "ctx_copy_txn": {
        "EN": "Copy Transaction Details",
        "DE": "Transaktionsdetails kopieren",
        "AR": "نسخ تفاصيل المعاملة",
    },

    # ── Phase 2: Empty States ───────────────────────────────────────────────
    "empty_inventory": {
        "EN": "No products yet",
        "DE": "Noch keine Produkte",
        "AR": "لا توجد منتجات بعد",
    },
    "empty_inventory_sub": {
        "EN": "Add your first product with Ctrl+N or the + button above.",
        "DE": "Fügen Sie Ihr erstes Produkt mit Strg+N oder der Schaltfläche + hinzu.",
        "AR": "أضف أول منتج باستخدام Ctrl+N أو زر + أعلاه.",
    },
    "empty_transactions": {
        "EN": "No transactions yet",
        "DE": "Noch keine Transaktionen",
        "AR": "لا توجد معاملات بعد",
    },
    "empty_transactions_sub": {
        "EN": "Stock movements will appear here as you add, remove, or adjust inventory.",
        "DE": "Bestandsbewegungen erscheinen hier, wenn Sie Bestände hinzufügen, entfernen oder anpassen.",
        "AR": "ستظهر حركات المخزون هنا عند إضافة أو إزالة أو تعديل المخزون.",
    },
    "empty_search": {
        "EN": "No results found",
        "DE": "Keine Ergebnisse gefunden",
        "AR": "لم يتم العثور على نتائج",
    },
    "empty_search_sub": {
        "EN": "Try a different search term or adjust your filters.",
        "DE": "Versuchen Sie einen anderen Suchbegriff oder passen Sie die Filter an.",
        "AR": "جرّب مصطلح بحث مختلف أو عدّل الفلاتر.",
    },
    "empty_reports": {
        "EN": "Select a report type to generate",
        "DE": "Wählen Sie einen Berichtstyp zum Erstellen",
        "AR": "اختر نوع التقرير لإنشائه",
    },

    # ── Phase 2: Bulk Operations ────────────────────────────────────────────
    "bulk_confirm_title": {
        "EN": "Bulk Operation",
        "DE": "Massenvorgang",
        "AR": "عملية مجمّعة",
    },
    "bulk_confirm_in": {
        "EN": "Stock In {qty} units for {n} selected items?",
        "DE": "Eingang von {qty} Einheiten für {n} ausgewählte Artikel?",
        "AR": "إدخال {qty} وحدة لـ {n} عناصر محددة؟",
    },
    "bulk_confirm_out": {
        "EN": "Stock Out {qty} units from {n} selected items?",
        "DE": "Ausgang von {qty} Einheiten für {n} ausgewählte Artikel?",
        "AR": "إخراج {qty} وحدة من {n} عناصر محددة؟",
    },
    "bulk_confirm_delete": {
        "EN": "Delete {n} selected products? This cannot be undone.",
        "DE": "{n} ausgewählte Produkte löschen? Dies kann nicht rückgängig gemacht werden.",
        "AR": "حذف {n} منتجات محددة؟ لا يمكن التراجع عن هذا.",
    },
    "bulk_qty_prompt": {
        "EN": "Quantity per item:",
        "DE": "Menge pro Artikel:",
        "AR": "الكمية لكل عنصر:",
    },
    "bulk_success": {
        "EN": "Bulk operation completed for {n} items.",
        "DE": "Massenvorgang für {n} Artikel abgeschlossen.",
        "AR": "تمت العملية المجمّعة لـ {n} عناصر.",
    },
    "bulk_note": {
        "EN": "Bulk {op}",
        "DE": "Massen-{op}",
        "AR": "{op} مجمّع",
    },
    "selected_n": {
        "EN": "{n} selected",
        "DE": "{n} ausgewählt",
        "AR": "{n} محدد",
    },

    # ── Phase 3: Sidebar nav ─────────────────────────────────────────────────
    "nav_suppliers": {
        "EN": "Suppliers",
        "DE": "Lieferanten",
        "AR": "الموردون",
    },
    "nav_sales": {
        "EN": "Sales",
        "DE": "Verkäufe",
        "AR": "المبيعات",
    },
    "nav_locations": {
        "EN": "Locations",
        "DE": "Standorte",
        "AR": "المواقع",
    },

    # ── Phase 3: Supplier management ─────────────────────────────────────────
    "admin_tab_suppliers": {
        "EN": "Suppliers",
        "DE": "Lieferanten",
        "AR": "الموردون",
    },
    "sup_col_name": {
        "EN": "Supplier Name",
        "DE": "Lieferantenname",
        "AR": "اسم المورد",
    },
    "sup_col_contact": {
        "EN": "Contact",
        "DE": "Kontakt",
        "AR": "جهة الاتصال",
    },
    "sup_col_phone": {
        "EN": "Phone",
        "DE": "Telefon",
        "AR": "الهاتف",
    },
    "sup_col_email": {
        "EN": "Email",
        "DE": "E-Mail",
        "AR": "البريد الإلكتروني",
    },
    "sup_col_address": {
        "EN": "Address",
        "DE": "Adresse",
        "AR": "العنوان",
    },
    "sup_col_notes": {
        "EN": "Notes",
        "DE": "Notizen",
        "AR": "ملاحظات",
    },
    "sup_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "sup_btn_add": {
        "EN": "+ Add Supplier",
        "DE": "+ Lieferant hinzufügen",
        "AR": "+ إضافة مورد",
    },
    "sup_btn_edit": {
        "EN": "Edit",
        "DE": "Bearbeiten",
        "AR": "تعديل",
    },
    "sup_btn_delete": {
        "EN": "Delete",
        "DE": "Löschen",
        "AR": "حذف",
    },
    "sup_btn_toggle": {
        "EN": "Toggle Active",
        "DE": "Aktiv umschalten",
        "AR": "تبديل النشاط",
    },
    "sup_add_title": {
        "EN": "Add Supplier",
        "DE": "Lieferant hinzufügen",
        "AR": "إضافة مورد",
    },
    "sup_edit_title": {
        "EN": "Edit Supplier",
        "DE": "Lieferant bearbeiten",
        "AR": "تعديل مورد",
    },
    "sup_delete_confirm": {
        "EN": "Delete {n} supplier(s)?",
        "DE": "{n} Lieferant(en) löschen?",
        "AR": "حذف {n} مورد(ين)؟",
    },
    "sup_delete_blocked": {
        "EN": "Cannot delete — supplier is linked to items with stock:",
        "DE": "Löschen nicht möglich — Lieferant ist mit Artikeln mit Bestand verknüpft:",
        "AR": "لا يمكن الحذف — المورد مرتبط بعناصر تحتوي على مخزون:",
    },
    "sup_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشط",
    },
    "sup_inactive": {
        "EN": "Inactive",
        "DE": "Inaktiv",
        "AR": "غير نشط",
    },
    "sup_name_required": {
        "EN": "Supplier name is required.",
        "DE": "Lieferantenname ist erforderlich.",
        "AR": "اسم المورد مطلوب.",
    },

    # ── Phase 3: Location management ─────────────────────────────────────────
    "admin_tab_locations": {
        "EN": "Locations",
        "DE": "Standorte",
        "AR": "المواقع",
    },
    "loc_col_name": {
        "EN": "Location Name",
        "DE": "Standortname",
        "AR": "اسم الموقع",
    },
    "loc_col_description": {
        "EN": "Description",
        "DE": "Beschreibung",
        "AR": "الوصف",
    },
    "loc_col_default": {
        "EN": "Default",
        "DE": "Standard",
        "AR": "افتراضي",
    },
    "loc_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "loc_btn_add": {
        "EN": "+ Add Location",
        "DE": "+ Standort hinzufügen",
        "AR": "+ إضافة موقع",
    },
    "loc_btn_edit": {
        "EN": "Edit",
        "DE": "Bearbeiten",
        "AR": "تعديل",
    },
    "loc_btn_delete": {
        "EN": "Delete",
        "DE": "Löschen",
        "AR": "حذف",
    },
    "loc_add_title": {
        "EN": "Add Location",
        "DE": "Standort hinzufügen",
        "AR": "إضافة موقع",
    },
    "loc_edit_title": {
        "EN": "Edit Location",
        "DE": "Standort bearbeiten",
        "AR": "تعديل موقع",
    },
    "loc_delete_confirm": {
        "EN": "Delete this location?",
        "DE": "Diesen Standort löschen?",
        "AR": "حذف هذا الموقع؟",
    },
    "loc_delete_blocked": {
        "EN": "Cannot delete — location has stock or is default.",
        "DE": "Löschen nicht möglich — Standort hat Bestand oder ist Standard.",
        "AR": "لا يمكن الحذف — الموقع يحتوي على مخزون أو هو الافتراضي.",
    },
    "loc_set_default": {
        "EN": "Set as Default",
        "DE": "Als Standard setzen",
        "AR": "تعيين كافتراضي",
    },
    "loc_is_default": {
        "EN": "Yes",
        "DE": "Ja",
        "AR": "نعم",
    },
    "loc_name_required": {
        "EN": "Location name is required.",
        "DE": "Standortname ist erforderlich.",
        "AR": "اسم الموقع مطلوب.",
    },
    "loc_transfer_title": {
        "EN": "Transfer Stock",
        "DE": "Bestand übertragen",
        "AR": "نقل المخزون",
    },
    "loc_transfer_from": {
        "EN": "From",
        "DE": "Von",
        "AR": "من",
    },
    "loc_transfer_to": {
        "EN": "To",
        "DE": "Nach",
        "AR": "إلى",
    },
    "loc_transfer_qty": {
        "EN": "Quantity",
        "DE": "Menge",
        "AR": "الكمية",
    },

    # ── Phase 3: Sales / POS ─────────────────────────────────────────────────
    "sales_title": {
        "EN": "Sales",
        "DE": "Verkäufe",
        "AR": "المبيعات",
    },
    "sales_new": {
        "EN": "New Sale",
        "DE": "Neuer Verkauf",
        "AR": "بيع جديد",
    },
    "sales_col_date": {
        "EN": "Date",
        "DE": "Datum",
        "AR": "التاريخ",
    },
    "sales_col_customer": {
        "EN": "Customer",
        "DE": "Kunde",
        "AR": "العميل",
    },
    "sales_col_items": {
        "EN": "Items",
        "DE": "Artikel",
        "AR": "العناصر",
    },
    "sales_col_total": {
        "EN": "Total",
        "DE": "Gesamt",
        "AR": "الإجمالي",
    },
    "sales_col_discount": {
        "EN": "Discount",
        "DE": "Rabatt",
        "AR": "الخصم",
    },
    "sales_col_net": {
        "EN": "Net Total",
        "DE": "Netto",
        "AR": "صافي المجموع",
    },
    "sales_no_items": {
        "EN": "Add at least one item to the sale.",
        "DE": "Fügen Sie mindestens einen Artikel zum Verkauf hinzu.",
        "AR": "أضف عنصرًا واحدًا على الأقل للبيع.",
    },
    "pos_title": {
        "EN": "Point of Sale",
        "DE": "Kasse",
        "AR": "نقطة البيع",
    },
    "pos_scan_or_search": {
        "EN": "Scan barcode or search…",
        "DE": "Barcode scannen oder suchen…",
        "AR": "مسح الباركود أو البحث…",
    },
    "pos_col_item": {
        "EN": "Item",
        "DE": "Artikel",
        "AR": "العنصر",
    },
    "pos_col_price": {
        "EN": "Price",
        "DE": "Preis",
        "AR": "السعر",
    },
    "pos_col_qty": {
        "EN": "Qty",
        "DE": "Anz",
        "AR": "الكمية",
    },
    "pos_col_subtotal": {
        "EN": "Subtotal",
        "DE": "Zwischensumme",
        "AR": "المجموع الفرعي",
    },
    "pos_customer_name": {
        "EN": "Customer Name (optional)",
        "DE": "Kundenname (optional)",
        "AR": "اسم العميل (اختياري)",
    },
    "pos_discount": {
        "EN": "Discount",
        "DE": "Rabatt",
        "AR": "الخصم",
    },
    "pos_total": {
        "EN": "Total",
        "DE": "Gesamt",
        "AR": "الإجمالي",
    },
    "pos_complete_sale": {
        "EN": "Complete Sale",
        "DE": "Verkauf abschließen",
        "AR": "إتمام البيع",
    },
    "pos_sale_success": {
        "EN": "Sale #{id} completed successfully!",
        "DE": "Verkauf #{id} erfolgreich abgeschlossen!",
        "AR": "تم إتمام البيع #{id} بنجاح!",
    },
    "pos_add_item": {
        "EN": "Add",
        "DE": "Hinzufügen",
        "AR": "إضافة",
    },
    "pos_remove_item": {
        "EN": "Remove",
        "DE": "Entfernen",
        "AR": "إزالة",
    },
    "pos_note": {
        "EN": "Note",
        "DE": "Notiz",
        "AR": "ملاحظة",
    },
    "pos_no_results": {
        "EN": "No items found.",
        "DE": "Keine Artikel gefunden.",
        "AR": "لم يتم العثور على عناصر.",
    },
    "pos_insufficient_stock": {
        "EN": "Insufficient stock for {name}: {available} available.",
        "DE": "Nicht genügend Bestand für {name}: {available} verfügbar.",
        "AR": "مخزون غير كافٍ لـ {name}: {available} متاح.",
    },

    # ── Phase 3: Expiry/Warranty ─────────────────────────────────────────────
    "dlg_lbl_expiry": {
        "EN": "Expiry Date",
        "DE": "Ablaufdatum",
        "AR": "تاريخ الانتهاء",
    },
    "dlg_lbl_warranty": {
        "EN": "Warranty Until",
        "DE": "Garantie bis",
        "AR": "الضمان حتى",
    },
    "alert_expiring_soon": {
        "EN": "{n} item(s) expiring within {days} days",
        "DE": "{n} Artikel läuft/laufen in {days} Tagen ab",
        "AR": "{n} عنصر(عناصر) ينتهي صلاحيتها خلال {days} يوم",
    },
    "alert_expired": {
        "EN": "{n} item(s) expired",
        "DE": "{n} Artikel abgelaufen",
        "AR": "{n} عنصر(عناصر) منتهية الصلاحية",
    },
    "dlg_alerts_tab_low":      {"EN": "Low Stock",    "DE": "Niedriger Bestand", "AR": "مخزون منخفض"},
    "dlg_alerts_tab_expiring": {"EN": "Expiring Soon","DE": "Bald ablaufend",    "AR": "تنتهي قريباً"},
    "dlg_alerts_tab_expired":  {"EN": "Expired",      "DE": "Abgelaufen",        "AR": "منتهية الصلاحية"},
    "expiry_col_expires":      {"EN": "Expires",      "DE": "Läuft ab",          "AR": "تاريخ الانتهاء"},
    "expiry_col_days_left":    {"EN": "Days Left",    "DE": "Tage übrig",        "AR": "أيام متبقية"},
    "expiry_empty_title":      {"EN": "No items expiring soon", "DE": "Keine ablaufenden Artikel", "AR": "لا توجد عناصر تنتهي قريباً"},
    "expired_empty_title":     {"EN": "No expired items",       "DE": "Keine abgelaufenen Artikel","AR": "لا توجد عناصر منتهية الصلاحية"},

    # ── Undo / Transaction Rollback ─────────────────────────────────────────
    "undo_not_found": {
        "EN": "Transaction not found",
        "DE": "Transaktion nicht gefunden",
        "AR": "لم يتم العثور على المعاملة",
    },
    "undo_not_stock_op": {
        "EN": "Only stock operations (IN/OUT/ADJUST) can be undone",
        "DE": "Nur Bestandsvorgänge (EIN/AUS/ANPASSEN) können rückgängig gemacht werden",
        "AR": "يمكن التراجع عن عمليات المخزون فقط (إدخال/إخراج/تعديل)",
    },
    "undo_already_undone": {
        "EN": "This transaction has already been undone",
        "DE": "Diese Transaktion wurde bereits rückgängig gemacht",
        "AR": "تم التراجع عن هذه المعاملة بالفعل",
    },
    "undo_expired": {
        "EN": "Undo window has expired (24 hours)",
        "DE": "Rückgängig-Zeitfenster abgelaufen (24 Stunden)",
        "AR": "انتهت فترة التراجع (24 ساعة)",
    },
    "undo_item_deleted": {
        "EN": "Item has been deleted — cannot undo",
        "DE": "Artikel wurde gelöscht — Rückgängig nicht möglich",
        "AR": "تم حذف العنصر — لا يمكن التراجع",
    },
    "undo_would_go_negative": {
        "EN": "Cannot undo — would result in negative stock",
        "DE": "Rückgängig nicht möglich — würde negativen Bestand ergeben",
        "AR": "لا يمكن التراجع — سيؤدي إلى مخزون سلبي",
    },
    "undo_success": {
        "EN": "Undone: stock {before} → {after}",
        "DE": "Rückgängig: Bestand {before} → {after}",
        "AR": "تم التراجع: المخزون {before} → {after}",
    },
    "undo_btn": {
        "EN": "Undo",
        "DE": "Rückgängig",
        "AR": "تراجع",
    },

    # ── Phase 4: Customer Management ─────────────────────────────────────────
    "admin_tab_customers": {
        "EN": "Customers",
        "DE": "Kunden",
        "AR": "العملاء",
    },
    "admin_nav_customers": {
        "EN": "CUSTOMERS",
        "DE": "KUNDEN",
        "AR": "العملاء",
    },
    "cust_page_title": {
        "EN": "Customer Management",
        "DE": "Kundenverwaltung",
        "AR": "إدارة العملاء",
    },
    "cust_page_desc": {
        "EN": "Manage your customer database and track purchase history",
        "DE": "Verwalten Sie Ihre Kundendatenbank und verfolgen Sie Kaufhistorien",
        "AR": "إدارة قاعدة بيانات العملاء وتتبع سجل المشتريات",
    },
    "cust_btn_add": {
        "EN": "+ Add Customer",
        "DE": "+ Kunde hinzufügen",
        "AR": "+ إضافة عميل",
    },
    "cust_col_name": {
        "EN": "Name",
        "DE": "Name",
        "AR": "الاسم",
    },
    "cust_col_phone": {
        "EN": "Phone",
        "DE": "Telefon",
        "AR": "الهاتف",
    },
    "cust_col_email": {
        "EN": "Email",
        "DE": "E-Mail",
        "AR": "البريد الإلكتروني",
    },
    "cust_col_purchases": {
        "EN": "Purchases",
        "DE": "Käufe",
        "AR": "المشتريات",
    },
    "cust_col_total_spent": {
        "EN": "Total Spent",
        "DE": "Gesamtausgaben",
        "AR": "إجمالي الإنفاق",
    },
    "cust_col_last_purchase": {
        "EN": "Last Purchase",
        "DE": "Letzter Kauf",
        "AR": "آخر شراء",
    },
    "cust_kpi_total": {
        "EN": "TOTAL CUSTOMERS",
        "DE": "KUNDEN GESAMT",
        "AR": "إجمالي العملاء",
    },
    "cust_kpi_active": {
        "EN": "ACTIVE",
        "DE": "AKTIV",
        "AR": "نشط",
    },
    "cust_kpi_with_purchases": {
        "EN": "WITH PURCHASES",
        "DE": "MIT KÄUFEN",
        "AR": "مع مشتريات",
    },
    "cust_dlg_add": {
        "EN": "New Customer",
        "DE": "Neuer Kunde",
        "AR": "عميل جديد",
    },
    "cust_dlg_edit": {
        "EN": "Edit Customer",
        "DE": "Kunde bearbeiten",
        "AR": "تعديل العميل",
    },
    "cust_lbl_name": {
        "EN": "Full Name",
        "DE": "Vollständiger Name",
        "AR": "الاسم الكامل",
    },
    "cust_lbl_phone": {
        "EN": "Phone Number",
        "DE": "Telefonnummer",
        "AR": "رقم الهاتف",
    },
    "cust_lbl_email": {
        "EN": "Email Address",
        "DE": "E-Mail-Adresse",
        "AR": "عنوان البريد الإلكتروني",
    },
    "cust_lbl_address": {
        "EN": "Address",
        "DE": "Adresse",
        "AR": "العنوان",
    },
    "cust_lbl_notes": {
        "EN": "Notes",
        "DE": "Notizen",
        "AR": "ملاحظات",
    },
    "cust_delete_confirm": {
        "EN": "Delete customer '{name}'? This cannot be undone.",
        "DE": "Kunde '{name}' löschen? Dies kann nicht rückgängig gemacht werden.",
        "AR": "حذف العميل '{name}'؟ لا يمكن التراجع عن هذا.",
    },
    "cust_delete_blocked": {
        "EN": "Cannot delete — customer has existing sales records.",
        "DE": "Kann nicht gelöscht werden — Kunde hat bestehende Verkaufsdaten.",
        "AR": "لا يمكن الحذف — العميل لديه سجلات مبيعات.",
    },
    "cust_saved": {
        "EN": "Customer saved successfully",
        "DE": "Kunde erfolgreich gespeichert",
        "AR": "تم حفظ العميل بنجاح",
    },
    "cust_name_required": {
        "EN": "Customer name is required",
        "DE": "Kundenname ist erforderlich",
        "AR": "اسم العميل مطلوب",
    },
    "cust_select_customer": {
        "EN": "Select Customer",
        "DE": "Kunde auswählen",
        "AR": "اختر العميل",
    },
    "cust_walk_in": {
        "EN": "Walk-in Customer",
        "DE": "Laufkunde",
        "AR": "عميل عابر",
    },
    "sidebar_customers": {
        "EN": "Customers",
        "DE": "Kunden",
        "AR": "العملاء",
    },
    "nav_customers": {
        "EN": "Customers",
        "DE": "Kunden",
        "AR": "العملاء",
    },
    # ── Audit ────────────────────────────────────────────────────────────────
    "aud_title": {
        "EN": "Inventory Audit",
        "DE": "Bestandsprüfung",
        "AR": "تدقيق المخزون",
    },
    "aud_subtitle": {
        "EN": "Conduct physical stock counts and reconcile with system",
        "DE": "Physische Bestandszählung und Abgleich durchführen",
        "AR": "إجراء جردة فعلية ومطابقة مع النظام",
    },
    "aud_btn_new": {
        "EN": "New Audit",
        "DE": "Neue Prüfung",
        "AR": "تدقيق جديد",
    },
    "aud_col_name": {
        "EN": "Audit Name",
        "DE": "Prüfungsname",
        "AR": "اسم التدقيق",
    },
    "aud_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "aud_col_started": {
        "EN": "Started",
        "DE": "Gestartet",
        "AR": "تم البدء",
    },
    "aud_col_completed": {
        "EN": "Completed",
        "DE": "Abgeschlossen",
        "AR": "مكتمل",
    },
    "aud_col_lines": {
        "EN": "Items",
        "DE": "Artikel",
        "AR": "العناصر",
    },
    "aud_col_counted": {
        "EN": "Counted",
        "DE": "Gezählt",
        "AR": "تم عده",
    },
    "aud_col_discrepancies": {
        "EN": "Discrepancies",
        "DE": "Abweichungen",
        "AR": "الفروقات",
    },
    "aud_col_actions": {
        "EN": "Actions",
        "DE": "Aktionen",
        "AR": "الإجراءات",
    },
    "aud_status_in_progress": {
        "EN": "In Progress",
        "DE": "Läuft",
        "AR": "قيد التنفيذ",
    },
    "aud_status_completed": {
        "EN": "Completed",
        "DE": "Abgeschlossen",
        "AR": "مكتمل",
    },
    "aud_status_cancelled": {
        "EN": "Cancelled",
        "DE": "Abgebrochen",
        "AR": "ملغى",
    },
    "aud_empty_title": {
        "EN": "No audits yet",
        "DE": "Noch keine Prüfungen",
        "AR": "لا توجد تدقيقات بعد",
    },
    "aud_empty_sub": {
        "EN": "Create a new audit to start counting inventory",
        "DE": "Erstellen Sie eine neue Prüfung, um mit der Bestandszählung zu beginnen",
        "AR": "قم بإنشاء تدقيق جديد لبدء عد المخزون",
    },
    "aud_dlg_title": {
        "EN": "New Inventory Audit",
        "DE": "Neue Bestandsprüfung",
        "AR": "تدقيق مخزون جديد",
    },
    "aud_dlg_name": {
        "EN": "Audit Name",
        "DE": "Prüfungsname",
        "AR": "اسم التدقيق",
    },
    "aud_dlg_notes": {
        "EN": "Notes (optional)",
        "DE": "Notizen (optional)",
        "AR": "ملاحظات (اختياري)",
    },
    "aud_kpi_total": {
        "EN": "Total Audits",
        "DE": "Prüfungen gesamt",
        "AR": "إجمالي التدقيقات",
    },
    "aud_kpi_progress": {
        "EN": "In Progress",
        "DE": "Läuft",
        "AR": "قيد التنفيذ",
    },
    "aud_kpi_completed": {
        "EN": "Completed",
        "DE": "Abgeschlossen",
        "AR": "مكتملة",
    },
    "aud_kpi_discrepancies": {
        "EN": "Total Discrepancies",
        "DE": "Abweichungen gesamt",
        "AR": "إجمالي الفروقات",
    },
    "aud_detail_back": {
        "EN": "Back to Audits",
        "DE": "Zurück zu Prüfungen",
        "AR": "العودة إلى التدقيقات",
    },
    "aud_detail_total": {
        "EN": "Total Items",
        "DE": "Artikel gesamt",
        "AR": "إجمالي العناصر",
    },
    "aud_detail_counted": {
        "EN": "Counted",
        "DE": "Gezählt",
        "AR": "تم عده",
    },
    "aud_detail_remaining": {
        "EN": "Remaining",
        "DE": "Verbleibend",
        "AR": "المتبقية",
    },
    "aud_detail_diff": {
        "EN": "Discrepancies",
        "DE": "Abweichungen",
        "AR": "الفروقات",
    },
    "aud_btn_complete": {
        "EN": "Complete Audit",
        "DE": "Prüfung abschließen",
        "AR": "إكمال التدقيق",
    },
    "aud_btn_apply": {
        "EN": "Apply Adjustments",
        "DE": "Änderungen anwenden",
        "AR": "تطبيق التعديلات",
    },
    "aud_btn_cancel_audit": {
        "EN": "Cancel Audit",
        "DE": "Prüfung abbrechen",
        "AR": "إلغاء التدقيق",
    },
    "aud_confirm_complete": {
        "EN": "Complete this audit? This action cannot be undone.",
        "DE": "Diese Prüfung abschließen? Diese Aktion kann nicht rückgängig gemacht werden.",
        "AR": "إكمال هذا التدقيق؟ لا يمكن التراجع عن هذا الإجراء.",
    },
    "aud_confirm_apply": {
        "EN": "Apply all discrepancies as stock adjustments? This will modify inventory levels.",
        "DE": "Alle Abweichungen als Bestandsanpassungen anwenden? Dies ändert die Bestandsstände.",
        "AR": "تطبيق جميع الفروقات كتعديلات مخزون؟ سيؤدي هذا إلى تعديل مستويات المخزون.",
    },
    "aud_confirm_cancel": {
        "EN": "Cancel this audit? Any counted items will be lost.",
        "DE": "Diese Prüfung abbrechen? Alle gezählten Artikel gehen verloren.",
        "AR": "إلغاء هذا التدقيق؟ سيتم فقدان جميع العناصر المعدودة.",
    },
    "aud_line_item": {
        "EN": "Item",
        "DE": "Artikel",
        "AR": "العنصر",
    },
    "aud_line_barcode": {
        "EN": "Barcode",
        "DE": "Strichcode",
        "AR": "الباركود",
    },
    "aud_line_system": {
        "EN": "System Qty",
        "DE": "Menge (System)",
        "AR": "الكمية (النظام)",
    },
    "aud_line_counted": {
        "EN": "Counted Qty",
        "DE": "Menge (Gezählt)",
        "AR": "الكمية (المعدودة)",
    },
    "aud_line_diff": {
        "EN": "Difference",
        "DE": "Differenz",
        "AR": "الفرق",
    },
    "aud_line_note": {
        "EN": "Note",
        "DE": "Notiz",
        "AR": "ملاحظة",
    },
    "aud_warn_name": {
        "EN": "Please enter an audit name",
        "DE": "Bitte geben Sie einen Prüfungsnamen ein",
        "AR": "يرجى إدخال اسم التدقيق",
    },
    "aud_search_ph": {
        "EN": "Search items...",
        "DE": "Artikel durchsuchen...",
        "AR": "البحث عن العناصر...",
    },
    "btn_cancel": {
        "EN": "Cancel",
        "DE": "Abbrechen",
        "AR": "إلغاء",
    },
    "btn_open": {
        "EN": "Open",
        "DE": "Öffnen",
        "AR": "فتح",
    },
    "error": {
        "EN": "Error",
        "DE": "Fehler",
        "AR": "خطأ",
    },
    "success": {
        "EN": "Success",
        "DE": "Erfolg",
        "AR": "نجح",
    },
    "confirm": {
        "EN": "Confirm",
        "DE": "Bestätigen",
        "AR": "تأكيد",
    },
    # ── Price Lists ───────────────────────────────────────────────────────────
    "pl_title": {
        "EN": "Price Lists & Margins",
        "DE": "Preislisten & Margen",
        "AR": "قوائم الأسعار والهوامش",
    },
    "pl_subtitle": {
        "EN": "Create and manage price lists, analyze margins and profitability",
        "DE": "Erstellen und verwalten Sie Preislisten, analysieren Sie Margen und Rentabilität",
        "AR": "إنشاء وإدارة قوائم الأسعار، تحليل الهوامش والربحية",
    },
    "pl_btn_new": {
        "EN": "New Price List",
        "DE": "Neue Preisliste",
        "AR": "قائمة أسعار جديدة",
    },
    "pl_tab_lists": {
        "EN": "Price Lists",
        "DE": "Preislisten",
        "AR": "قوائم الأسعار",
    },
    "pl_tab_margins": {
        "EN": "Margin Analysis",
        "DE": "Margenanalyse",
        "AR": "تحليل الهوامش",
    },
    "pl_col_name": {
        "EN": "Name",
        "DE": "Name",
        "AR": "الاسم",
    },
    "pl_col_desc": {
        "EN": "Description",
        "DE": "Beschreibung",
        "AR": "الوصف",
    },
    "pl_col_items": {
        "EN": "Items",
        "DE": "Artikel",
        "AR": "العناصر",
    },
    "pl_col_status": {
        "EN": "Status",
        "DE": "Status",
        "AR": "الحالة",
    },
    "pl_col_created": {
        "EN": "Created",
        "DE": "Erstellt",
        "AR": "تم الإنشاء",
    },
    "pl_col_actions": {
        "EN": "Actions",
        "DE": "Aktionen",
        "AR": "الإجراءات",
    },
    "pl_status_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشط",
    },
    "pl_status_inactive": {
        "EN": "Inactive",
        "DE": "Inaktiv",
        "AR": "غير نشط",
    },
    "pl_empty_title": {
        "EN": "No Price Lists",
        "DE": "Keine Preislisten",
        "AR": "لا توجد قوائم أسعار",
    },
    "pl_empty_sub": {
        "EN": "Create a price list to get started",
        "DE": "Erstellen Sie eine Preisliste zum Starten",
        "AR": "إنشاء قائمة أسعار للبدء",
    },
    "pl_dlg_title": {
        "EN": "New Price List",
        "DE": "Neue Preisliste",
        "AR": "قائمة أسعار جديدة",
    },
    "pl_dlg_edit_title": {
        "EN": "Edit Price List",
        "DE": "Preisliste bearbeiten",
        "AR": "تحرير قائمة الأسعار",
    },
    "pl_dlg_name": {
        "EN": "List Name",
        "DE": "Listenname",
        "AR": "اسم القائمة",
    },
    "pl_dlg_desc": {
        "EN": "Description",
        "DE": "Beschreibung",
        "AR": "الوصف",
    },
    "pl_dlg_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشط",
    },
    "pl_kpi_total": {
        "EN": "Total Lists",
        "DE": "Preislisten gesamt",
        "AR": "إجمالي القوائم",
    },
    "pl_kpi_active": {
        "EN": "Active",
        "DE": "Aktiv",
        "AR": "نشطة",
    },
    "pl_kpi_items": {
        "EN": "Items Priced",
        "DE": "Preisartikel",
        "AR": "العناصر المسعرة",
    },
    "pl_kpi_margin": {
        "EN": "Avg Margin",
        "DE": "Durchschnittliche Marge",
        "AR": "المتوسط الهامش",
    },
    "pl_detail_back": {
        "EN": "← Back",
        "DE": "← Zurück",
        "AR": "← رجوع",
    },
    "pl_btn_add_all": {
        "EN": "Add All Items",
        "DE": "Alle Artikel hinzufügen",
        "AR": "إضافة جميع العناصر",
    },
    "pl_btn_markup": {
        "EN": "Bulk Markup",
        "DE": "Massenmarkierung",
        "AR": "ترميز جماعي",
    },
    "pl_btn_apply": {
        "EN": "Apply to Inventory",
        "DE": "Auf Bestand anwenden",
        "AR": "تطبيق على المخزون",
    },
    "pl_confirm_apply": {
        "EN": "Apply this price list to all items in inventory?",
        "DE": "Diese Preisliste auf alle Bestandsartikel anwenden?",
        "AR": "تطبيق قائمة الأسعار هذه على جميع العناصر في المخزون؟",
    },
    "pl_confirm_delete": {
        "EN": "Delete this price list?",
        "DE": "Diese Preisliste löschen?",
        "AR": "حذف قائمة الأسعار هذه؟",
    },
    "pl_markup_title": {
        "EN": "Bulk Markup",
        "DE": "Massenmarkierung",
        "AR": "ترميز جماعي",
    },
    "pl_markup_pct": {
        "EN": "Increase prices by percentage:",
        "DE": "Preise um Prozentsatz erhöhen:",
        "AR": "زيادة الأسعار بنسبة مئوية:",
    },
    "pl_col_item": {
        "EN": "Item",
        "DE": "Artikel",
        "AR": "العنصر",
    },
    "pl_col_barcode": {
        "EN": "Barcode",
        "DE": "Barcode",
        "AR": "الباركود",
    },
    "pl_col_current": {
        "EN": "Current Price",
        "DE": "Aktueller Preis",
        "AR": "السعر الحالي",
    },
    "pl_col_list_price": {
        "EN": "List Price",
        "DE": "Listenpreis",
        "AR": "سعر القائمة",
    },
    "pl_col_cost": {
        "EN": "Cost",
        "DE": "Kosten",
        "AR": "التكلفة",
    },
    "pl_col_margin_pct": {
        "EN": "Margin %",
        "DE": "Marge %",
        "AR": "الهامش %",
    },
    "pl_col_margin_amt": {
        "EN": "Margin Amount",
        "DE": "Margenbetrag",
        "AR": "مبلغ الهامش",
    },
    "pl_col_stock": {
        "EN": "Stock",
        "DE": "Bestand",
        "AR": "المخزون",
    },
    "pl_col_profit": {
        "EN": "Potential Profit",
        "DE": "Potenzieller Gewinn",
        "AR": "الربح المحتمل",
    },
    "pl_search_ph": {
        "EN": "Search...",
        "DE": "Suchen...",
        "AR": "ابحث...",
    },
    "pl_ctx_open": {
        "EN": "Open",
        "DE": "Öffnen",
        "AR": "فتح",
    },
    "pl_ctx_edit": {
        "EN": "Edit",
        "DE": "Bearbeiten",
        "AR": "تحرير",
    },
    "pl_ctx_delete": {
        "EN": "Delete",
        "DE": "Löschen",
        "AR": "حذف",
    },
    "pl_ctx_apply": {
        "EN": "Apply to Inventory",
        "DE": "Auf Bestand anwenden",
        "AR": "تطبيق على المخزون",
    },
    "pl_warn_name": {
        "EN": "Please enter a name for the price list",
        "DE": "Bitte geben Sie einen Namen für die Preisliste ein",
        "AR": "يرجى إدخال اسم لقائمة الأسعار",
    },
    "pl_margin_low": {
        "EN": "Low margin",
        "DE": "Niedrige Marge",
        "AR": "هامش منخفض",
    },
    "pl_margin_mid": {
        "EN": "Medium margin",
        "DE": "Mittlere Marge",
        "AR": "هامش متوسط",
    },
    "pl_margin_high": {
        "EN": "High margin",
        "DE": "Hohe Marge",
        "AR": "هامش عالي",
    },
}


# ── Color name translations ───────────────────────────────────────────────────
# Keys are English palette names (same as stored in DB). Never change the keys.

_COLORS: dict[str, dict[str, str]] = {
    "Red":      {"DE": "Rot",             "AR": "أحمر"},
    "Orange":   {"DE": "Orange",          "AR": "برتقالي"},
    "Yellow":   {"DE": "Gelb",            "AR": "أصفر"},
    "Green":    {"DE": "Grün",            "AR": "أخضر"},
    "Mint":     {"DE": "Minze",           "AR": "نعناعي"},
    "Teal":     {"DE": "Petrol",          "AR": "أزرق مخضر"},
    "Cyan":     {"DE": "Cyan",            "AR": "سماوي"},
    "Blue":     {"DE": "Blau",            "AR": "أزرق"},
    "Indigo":   {"DE": "Indigo",          "AR": "نيلي"},
    "Purple":   {"DE": "Lila",            "AR": "بنفسجي"},
    "Pink":     {"DE": "Rosa",            "AR": "وردي"},
    "Rose":     {"DE": "Rose",            "AR": "وردة"},
    "Coral":    {"DE": "Koralle",         "AR": "مرجاني"},
    "Brown":    {"DE": "Braun",           "AR": "بني"},
    "Beige":    {"DE": "Beige",           "AR": "بيج"},
    "Gold":     {"DE": "Gold",            "AR": "ذهبي"},
    "Olive":    {"DE": "Olivgrün",        "AR": "زيتوني"},
    "Maroon":   {"DE": "Kastanienbraun",  "AR": "كستنائي"},
    "Navy":     {"DE": "Marine",          "AR": "كحلي"},
    "Black":    {"DE": "Schwarz",         "AR": "أسود"},
    "Charcoal": {"DE": "Anthrazit",       "AR": "فحمي"},
    "Gray":     {"DE": "Grau",            "AR": "رمادي"},
    "Silver":   {"DE": "Silber",          "AR": "فضي"},
    "White":    {"DE": "Weiß",            "AR": "أبيض"},
}


_NOTE_MAP = {"Product created": "note_product_created"}


def note_t(raw: str) -> str:
    """Translate known DB-stored note strings; pass through unknown ones."""
    key = _NOTE_MAP.get(raw)
    return t(key) if key else raw


def color_t(english_name: str) -> str:
    """Return translated color name. Falls back to English if no translation."""
    if LANG == "EN":
        return english_name
    return _COLORS.get(english_name, {}).get(LANG, english_name)


def set_lang(lang: str) -> None:
    """Switch active language and update Qt layout direction."""
    global LANG
    LANG = lang if lang in ("EN", "DE", "AR") else "EN"
    app = QApplication.instance()
    if app:
        direction = Qt.LayoutDirection.RightToLeft if LANG == "AR" else Qt.LayoutDirection.LeftToRight
        app.setLayoutDirection(direction)


def t(key: str, **kwargs) -> str:
    """Return translated string for current language, formatted with kwargs."""
    entry = _TR.get(key, {})
    text  = entry.get(LANG) or entry.get("EN") or key
    return text.format(**kwargs) if kwargs else text
