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
        "EN": "  Products  ",
        "DE": "  Produkte  ",
        "AR": "  المنتجات  ",
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
    # ── Transaction table columns ─────────────────────────────────────────────
    "col_datetime":  {"EN": "Date & Time", "DE": "Datum & Zeit",   "AR": "التاريخ والوقت"},
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
    "btn_edit":      {"EN": "  \u270E  Edit",        "DE": "  \u270E  Bearbeiten", "AR": "  \u270E  تعديل"},
    "btn_delete":    {"EN": "  \u2715  Delete",      "DE": "  \u2715  Löschen",    "AR": "  \u2715  حذف"},
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
    "dlg_lbl_brand":      {"EN": "Brand *",          "DE": "Marke *",                  "AR": "العلامة *"},
    "dlg_lbl_type":       {"EN": "Type *",           "DE": "Typ *",                    "AR": "النوع *"},
    "dlg_lbl_color":      {"EN": "Color",             "DE": "Farbe",                    "AR": "اللون"},
    "dlg_lbl_barcode":    {"EN": "Barcode",          "DE": "Barcode",                  "AR": "الباركود"},
    "dlg_lbl_init_stock": {"EN": "Initial Stock",   "DE": "Anfangsbestand",            "AR": "المخزون الأولي"},
    "dlg_lbl_alert_when": {"EN": "Alert when ≤",    "DE": "Alarm wenn ≤",              "AR": "تنبيه عند ≤"},
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
        "EN": "Physical Count (Inventur)",
        "DE": "Körperliche Zählung (Inventur)",
        "AR": "الجرد الفعلي (Inventur)",
    },
    "disp_sys_stock": {
        "EN": "System stock: {n}",
        "DE": "Systembestand: {n}",
        "AR": "مخزون النظام: {n}",
    },
    "disp_phys_count": {"EN": "Physical count:", "DE": "Physische Zählung:", "AR": "العدد الفعلي:"},
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
        "EN": "Double-click to record physical count (Inventur)",
        "DE": "Doppelklick zur Erfassung des Inventurs",
        "AR": "انقر مرتين لتسجيل الجرد الفعلي",
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
