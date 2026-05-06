# Changelog

All notable changes to **Stock Manager Pro** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [2.5.3] - 2026-05-06


## [2.5.3] - 2026-05-06

### Fixed — `(D.D) Soft-OLED` and `(D.D) Soft-OLED Diagnose` collided on `DDSO`
- **Root cause**: the v2.5.1 `_PART_TYPE_OVERRIDES` table only had three (D.D)-family keys (`"(d.d) soft oled"`, `"(d.d) soft-oled"`, `"(d.d) soft-oled diagn"`). Any spelling variation — `"Diagnose"` instead of `"Diagn"`, space instead of hyphen, or both at once — fell through to the generic 4-char fallback which produces `DDSO` (parens "DD" + word-initials "SO/SOD" trimmed to 4 chars). When a user has both `(D.D) Soft-OLED` (override hit → `DD`) and `(D.D) Soft-OLED Diagnose` (fallback → `DDSO`) the codes are different — but if the user has TWO diagnostic-variants spelled differently (e.g. one with `Diagn`, one with `Diagnose`) they BOTH fall through to the same fallback `DDSO` and silently collide. The user reported both iPhone OLED variants showing the same `DD-SO` code on the sticker.
- **Fix**: introduced `_normalize_pt_name(name)` that aggressively normalises before override lookup — replaces `-` and `_` with spaces, collapses runs of whitespace, and unifies every diagnostic-family word (`diagnose`, `diagnostic`, `diagnostics`, `diagnosis`) to the canonical `diagn`. Override keys are stored in the same normalised form. Verified against 22 plausible spellings: every `(D.D) Soft-OLED` variant resolves to `DSO` (5+ spellings), every `(D.D) Soft-OLED + diagnostic` variant resolves to `DSD` (7+ spellings including `Diagn`, `Diagnose`, `Diagnostic`, `Diagnostics`, `Diagnosis`).
- **Hybrid `D` + 2-char product mnemonic codes** for the entire (D.D) family — picked over abstract `DD`/`DDD` so codes read meaningfully on the sticker:
  - `(D.D) Soft-OLED`           → `DSO`  (D.D + Soft-Oled)
  - `(D.D) Soft-OLED Diagn(*)`  → `DSD`  (D.D + Soft-Diagnose)
  - `(D.D) Hard-OLED`           → `DHO`
  - `(D.D) Hard-OLED Diagn(*)`  → `DHD`
  - `(D.D) OLED`                → `DOL`
  - `(D.D) OLED Diagn(*)`       → `DOD`
- The leading `D` keeps the `(D.D)` brand identity in the code, so a future plain `Soft-OLED` from a different supplier (which falls through to the generic `SO` fallback) doesn't collide. Width: `DSO` is 1 char wider than the old `DD`, but every iPhone payload (4-char model + 3-char part-type + colour = 14 chars at 49.2 mm) still fits the 50 mm sticker comfortably. Verified end-to-end via `_make_barcode_text`.
- **User action required**: tick **Regenerate (overwrite existing)** + **Generate** + **Assign & Save** on the Barcode Generator page to refresh stored codes. Old printed labels still scan against the canonicalised DB rows because the override applies at both write and read time, but stored barcode strings only update via regenerate.

### Fixed — `logs/stock_manager.log` was being tracked in git
- The runtime log file was inadvertently committed across v2.4.7 → v2.5.2 — every release pushed several MB of local log output to GitHub. Untracked the file via `git rm --cached` (file remains on disk and the app keeps writing to it normally) and added `logs/` + `*.log` to `stock-manager/.gitignore` so it can't sneak back in. Historical log content remains in the commit history; a follow-up `git filter-repo` could scrub it if size becomes a concern, but that's a destructive operation we shouldn't run without explicit consent.

## [2.5.2] - 2026-05-06

### Fixed — Scan-to-add round trip ("Galaxy A15 4G doesn't save")
- **Root cause**: `ItemRepository.add_product` and `update_product` stored the barcode argument with only `.strip()` applied — no scanner-mark prefix removal — while `get_by_barcode` always normalised the input via `normalize_barcode`. When a user scanned an unknown barcode, `MainWindow._barcode` passed the **raw** scanner output (e.g. `aSAßA154ßOLßBK`, with the `a` prefix) into `_add_product(preset_barcode=…)`, the dialog set that raw form into the barcode field, and the save wrote `aSAßA154ßOLßBK` to the DB. On the next scan, `get_by_barcode` stripped the `a` prefix and queried `SAßA154ßOLßBK` — which the DB didn't have (it had the prefix-included form). Same barcode, two different stored strings, never matched. The user's intuition that it was "the a at the beginning" was correct. The bug was symptom-free as long as items came in via barcode-generator + Assign & Save (those use the canonical form), which is why it stayed hidden until the user added a model via scan-to-add. **Affects ALL scan-to-add inserts since v2.4.8** (when the V17 migration cleaned legacy data but the write-path wasn't fixed), not just A15.
- **Fix**: introduced `canonical_barcode(text)` in `app/services/barcode_gen_service.py` — the single source of truth for the DB-canonical form — and applied it at every barcode write site (`add_product`, `update_product`, `update_barcode`, `bulk_update_barcodes`) and read site (`get_by_barcode`). Also canonicalised `preset_barcode` in `inventory_ops.add_product` so the dialog shows the user the same string that will actually be stored.
- **Migration V18 → V19** rewrites any existing rows that leaked through the bug since V17 — re-applies the scanner-mark prefix strip (same heuristic as V17) on `inventory_items.barcode` and `app_config` command/colour barcode rows.

### Fixed — Galaxy S10+ printed labels not scannable
- **Root cause**: the K30F + YunPrint Code 128 renderer produces visual artifacts on the `+` character — the user's "lines pushed to other lines" symptom. The encoding is technically valid, but the printed bars overlap into adjacent positions and the resulting sticker fails to decode regardless of payload length (the user reported failure on a 13-char `SA-S10+-OS-BK` payload that should have fit comfortably). Affects every payload that contains `+`: OnePlus brand "1+", PRO+ marker "P+" (Note 14 Pro+, Pixel 6a Pro+, etc.), literal Plus models "S10+", "S20+", "S22+", "Note 10+".
- **Fix**: substitute `+` → `P` in `_make_barcode_text` so the generator never emits `+` in a payload. `1+` (OnePlus brand) becomes `1P`, `P+` (Pro+ suffix) becomes `PP`, `S10+` (literal model) becomes `S10P`. The substitution is also applied symmetrically in `canonical_barcode`, so existing physical labels printed with `+` continue to scan against the canonicalised DB rows after the V19 migration rewrites them — old labels in shop don't have to be re-printed for lookups to keep working.
- **Migration V18 → V19** also runs `REPLACE(barcode, '+', 'P')` on `inventory_items.barcode` and `app_config` so the stored DB rows are P-form. Verified end-to-end: `SA-S10P-OS-BK` (was `SA-S10+-OS-BK`) renders cleanly and decodes 100% in zxing-cpp at K30F-grade settings. Width unchanged (13 chars, 46.4 mm — well inside the 50 mm sticker budget).

### Notes for the user
- After updating to v2.5.2, the V19 migration runs automatically on first launch. No manual action required.
- Existing physical labels printed with `+` continue to scan because `canonical_barcode` substitutes at lookup time. New regenerations produce P-form labels that print without the YunPrint render artifact.
- For new items, the scan-to-add round trip is now correct: scan unknown → "add product" dialog (shows canonical form) → save → re-scan → finds the item.

## [2.5.1] - 2026-05-02

### Fixed — 100% scannable label printer barcodes
- **Root cause**: The K30F is a 203 DPI thermal printer (8 dots/mm = 0.125 mm per dot). Code 39 needs ~16 modules per character + start/stop overhead; an 18-character payload like `XI-NOTE14P+-OSP-SV` requires ≥ 0.25 mm narrow bar to decode reliably, which makes the symbol ~85 mm wide. On a 50 mm sticker, YunPrint silently shrinks bars below the decode floor (down to 0.18-0.20 mm narrow), the 2.5:1 wide:narrow ratio collapses into integer-dot rounding errors, and the scanner can't lock on. Verified empirically with `zxing-cpp` decoding the rendered output: at 0.20 mm narrow, the long Xiaomi payload decodes 0% of the time; at 0.25 mm and above, 100%.
- **Pre-export decode validation** (`BarcodeGenService.validate_scannability`). Every barcode in a batch is now rendered at K30F-grade settings (203 DPI, 0.25 mm narrow bar, 1.0 mm quiet zone, 1-bit B&W threshold to simulate the thermal head's binary output) and decoded back with `zxing-cpp`. Anything that doesn't decode, or whose printed width exceeds the configured sticker width, is reported up to the UI which **refuses to write the CSV** rather than silently exporting unscannable labels. Optional dependency — install with `pip install zxing-cpp`; without it, the width-fit check still runs.
- **Quiet zone calibrated against real K30F output**: validation defaults to 1.0 mm quiet zone instead of ISO/IEC's textbook 2.5 mm. zxing-cpp + the user's handheld scanner decode 100% at 0.5 mm in benchmarks; 1.0 mm leaves a 2-X-dim safety margin without wasting 4 mm of the 50 mm sticker. The post-export instructions tell the user to set their YunPrint template's quiet zone to ≤ 1.0 mm to match — bigger zones in YunPrint will overflow the sticker even when our validator passes. First user feedback on a 1071-entry catalogue: pass rate jumped from 30% (at the old 2.0 mm default) to ~95%, with the remaining ~5% being genuine 15+ char outliers (Galaxy A04S/A05S OLED + colour, Xiaomi Note 14 Pro+ ORG-Service-Pack + colour) that need either a wider sticker roll OR per-colour barcodes off.
- **`BarcodeValidationError`** carries the failed entries, the oversize entries, and the symbology used, so the UI can show a per-entry breakdown ("Redmi Note 14 Pro+ ORG-Service-Pack Silver → 62.2 mm wide, sticker is 50 mm"). The export dialog offers four actions: switch to Code 128, regenerate with shorter abbreviations, untick per-color barcodes (3 chars saved), or print anyway with a clear "may not scan" warning.
- **Code 128 is now the default symbology** (was Code 39). At the same payload, Code 128 is ~40% denser than Code 39 (11 modules per character vs 13-16) and adds a built-in mod-103 checksum that catches print-bleed damage Code 39 can't detect. Switching is a template-only change in YunPrint — the DB barcode value is byte-identical, so existing Code 39 labels stuck on shop items keep working without migration. Code 39 stays available via the Format radio for users with Code-39-only scanner setups.
- **Curated `_PART_TYPE_OVERRIDES` table** (~30 entries) for the most common phone-repair part types — the real width-killer in production data. `OLED` → `OL` (was `OLED`, saves 2 chars), `Battery` → `BT`, `Back Cover` → `BC`, `(D.D) Soft-OLED` → `DD`, `(JK) incell FHD` → `JK`, `ORG Service Pack` → `OSP`, etc. Lookup is case- and whitespace-insensitive; anything not in the table falls through to the generic abbreviation logic, so this is purely additive — won't break codes for part types you haven't curated yet. Empirical impact on a 1071-entry catalogue: brought oversize count from 573 → 328 in one pass.
- **Radio-generation suffix shorthand** in `_WORD_MAP`: `5G` → `5`, `4G` → `4`, `3G` → `3`. The two-letter form pushed `Galaxy A52s 5G + OLED + colour` and `Galaxy A13 4G + ORG-Service-Pack + colour` from a fitting 14 chars to a non-fitting 15 chars (51.9 mm > 50 mm sticker). One-digit form reads back unambiguously given the brand prefix (`SA-A52S5` is "Samsung Galaxy A52s 5G"; `SA-A134` is "Samsung Galaxy A13 4G") and rescued ~300 entries on the user's catalogue. Verified against zxing-cpp: no decode collisions vs the previous form because brand+model+part+colour is still globally unique.
- **`OSP` → `OS`** in the override table for ORG Service Pack (was 3 chars, now 2). This was the last 1-char-over-budget pattern: `XX-MMMMM-OSP-CC` (5-char model + colour) is exactly 15 chars at 51.9 mm, just over the 50 mm sticker; trimming to `XX-MMMMM-OS-CC` brings it to 14 chars at 49.2 mm. Within the part-type slot of a barcode payload the 2-char form is unambiguous (no other override starts with "O" at length 2). On the user's catalogue this rescued the Galaxy A52s 5G / S20 FE / A13 4G × ORG Service Pack × colour variants — ~180 items.
- **`NOTE` → `N`** in `_WORD_MAP`. The Redmi Note 11 / 11 Pro / 12 Pro / 14 Pro+ family and Galaxy Note 10 / 20 Ultra family all carry the 4-letter `NOTE` prefix, which inflates the model code from a fitting 3-char form (`N11`, `N20U`) to a non-fitting 6-7 char form (`NOTE11`, `NOTE20U`). The 1-letter shorthand is unambiguous within a brand prefix — `XI-N14P+` reads back as "Xiaomi Note 14 Pro+", `SA-N20U` as "Samsung Galaxy Note 20 Ultra". Verified no collision with `Nord` (different word, kept whole) or other N-prefixed model lines.
- **Combined catalogue impact**: pass rate climbed from 30% (pre-v2.5.1) → 46.5% (after QZ tuning) → 69.4% (after part-type overrides) → 82.8% (after 5G/4G shorthand) → 86.6% (after OSP shorthand) → **~100%** (after NOTE shorthand). With this round all known failure patterns on the user's 1071-entry catalogue fit a 50 mm K30F sticker at safe density.
- **Tightened part-type fallback length**: `_part_type_code(max_len=4)` (was 5). Caps unrecognised part-type codes at 4 chars so novel terms can't blow the sticker budget. Note: `_abbreviate(max_len=8)` is **kept at 8** — an attempt to drop it to 6 caused a collision regression where `Note 14 Pro+` and `Note 14 Pro` both truncated to `NOTE14`, merging two distinct phones onto the same code; the override table fixes the width problem without sacrificing model identity.
- **"Verify" button** on the Barcode Generator page runs `validate_scannability` against the current entries WITHOUT writing any files — lets users sanity-check a regenerated batch before deciding whether to assign-and-save. Reports per-entry pass/fail with widths, payload preview, and rejection reason.
- **Post-export instructions dialog** now includes a **K30F + YunPrint template settings checklist** tailored to the chosen symbology — narrow bar ≥ 0.30 mm (≥ 0.25 mm absolute minimum), quiet zone ≥ 2.5 mm, bar height ≥ 8 mm, print darkness 70-80%, slow-medium speed. The template settings are the only remaining failure surface once encoding is validated software-side.
- **Module-level documentation** at the top of `barcode_gen_service.py` walks through the K30F failure mode in detail — the dot-pitch math, the ratio-collapse mechanism, the empirical decode floor by symbology, and the user-side checklist. Future maintainers (and future me) can read the why before touching the validation thresholds.

### Fixed — `_item_repo` reference bug on Barcode Generator page
- **The "X items match" live counter was always showing 0** because `_item_repo` was referenced in `BarcodeGenPage._refresh_count` but never imported (the surrounding `try/except Exception` swallowed the `NameError` silently and fell through to the `n=0` path). Added the missing `from app.repositories.item_repo import ItemRepository` and module-level `_item_repo = ItemRepository()`. The counter now updates correctly as the user adjusts brand / category / model / part-type filters, so they can spot a too-broad scope before clicking Generate.

## [2.5.0] - 2026-04-29

### Added — Bulk split labels-print export
- **"Export for YunPrint" now supports splitting** the output into multiple files in one click. After Generate, the Export button opens a small dialog asking how to split:
  - **Single file** (legacy behaviour) — one combined `.txt`
  - **Split by Part Type** (default — most common request) — one file per JK / D.D / ORG-Service-Pack / Battery / etc., so each goes to its own sticker template / roll
  - **Split by Brand** — one file per Apple / Samsung / Xiaomi
  - **Split by Brand + Part Type** — finest granularity
  - **Split by Model** — one file per phone model
- **Professional naming convention**: every file follows `labels-print-<group>-<YYYY-MM-DD>.txt`, with group names sanitised so brand / part-type names with spaces, dots, slashes, or parens become safe filenames on every OS (e.g. `(D.D) Soft-OLED` → `D_D_Soft-OLED`). Generic `labels-print-` prefix (not vendor-specific) so the same files work with any label printer that imports CSV — YunPrint, Brady, NiceLabel, etc. Multiple batches across multiple days can coexist in one folder and Explorer's name-sort gives a clean chronological listing.
- **Verified end-to-end** on a 1071-entry Apple+Samsung+Xiaomi catalogue: split-by-part-type produced 7 files (`OLED` 488 rows, `JK_incell_FHD` 23 rows, etc.), split-by-brand produced 3 files (Apple 95, Samsung 752, Xiaomi 224), split-by-brand-part-type produced 9 files. Empty groups skipped silently — no zero-row files cluttering the folder.
- New `BarcodeGenService.export_for_yunprint_split(entries, output_dir, split_by)` returns `[(path, count), …]` so the UI can show a per-file summary in the success dialog. The legacy `export_for_yunprint` is now a thin wrapper around the same internal `_write_yunprint_csv` helper, so single-file output stays byte-identical to before — no risk of regression on existing workflows.
- Export button on Barcode Generator page opens a split-mode chooser (radio buttons, default Part Type), then the appropriate file/directory picker. Status bar shows `"X rows in N file(s)"` on success and the post-export dialog lists the first 10 generated files plus `"… and N more"` for larger batches; folder opens in Explorer via `QDesktopServices.openUrl` so the user can drag the .txt straight into the YunPrint app.

## [2.4.10] - 2026-04-29

### Added — Matrix tab Excel-like filter + Σ stats
- **Multi-word AND search** in the matrix toolbar — type natural sentences like `samsung galaxy s22 ultra` or `redmi note 14 pro` and every word must appear somewhere in the row's haystack (order doesn't matter, case-insensitive). 150 ms debounce so typing doesn't re-walk the table on every keystroke. **Enter** applies immediately (skip the wait); **Esc** clears the search.
- **Brand-aware smart search**: typing the product line you say out loud — `iphone` / `galaxy` / `redmi` / `pixel` — works even though the model column only shows the model number (`11 Pro` / `S22` / `Note 14`). The filter prepends the section's brand AND its line aliases (Apple→iphone/ipad, Samsung→galaxy/note, Xiaomi→redmi/poco/mi, Huawei→mate/p/nova/y, Honor→magic, Google→pixel, OnePlus→nord) to each row's haystack before matching. Verified end-to-end: `iphone` → 24 Apple matches / 0 elsewhere; `galaxy` → 376 Samsung; `redmi` → 112 Xiaomi; `redmi note 14` → 3 specific matches; `samsung galaxy s22` → 3 specific matches.
- **Live match-count label** next to the search box — `"24 matching rows"` / `"No rows match"` / hidden when the filter is empty. Always-visible feedback so the user knows the filter narrowed correctly without having to count rows.
- **Empty brand sections hide entirely** in multi-brand mode — when zero models in a section match, both the section's `QLabel` header AND its container disappear, instead of a stray "Samsung" header floating over an empty gap.
- **Filter hides BOTH frozen model column AND data table in lockstep** so vertical alignment is preserved — earlier draft only hid the data table, leaving model names visible against blank gaps. Implementation lives on `FrozenMatrixContainer.filter_rows` so it can drive both child tables (`_model_table` + `_table`) atomically.
- **Brand-context fallback**: each `FrozenMatrixContainer` is now tagged with a `_section_brand` attribute (set by `MatrixTab._add_brand_section` / `_reload_brand_container` for multi-brand views, and by the single-brand path on the brand combo selection). The filter uses this when the container has no internal brand-header rows.
- **Empty brand sections are hidden** when every model under them is filtered out — otherwise a "Samsung" header would float over an empty gap. The two-pass walk decides per-model visibility first, then per-brand-header visibility based on whether any model under it survived.
- **Series separators (the 3px coloured stripes between iPhone 11/12/13/14 series, Galaxy S22/S23 series, etc.) hide along with the models on either side**. Earlier draft kept all separators visible "for context" — but with a narrow filter (e.g. `XS`) that left a stack of orphan 3px stripes underneath the single visible row, looking like a striped grey band. Now a separator is only shown if there's a visible model row BOTH before AND after it within the same brand section; orphan stripes hide along with the rows they used to separate.
- **Quick-filter chips** for the four most common stock states — `All` / `Low` (`0 < stock ≤ min`) / `Out` (`stock = 0` with `min > 0`) / `Reorder` (`stock < min`). Single-select; the active chip carries the accent fill. Filters compose with the search box (text AND state).
- **Σ Selection statistics** readout in the toolbar — `Σ count=… sum=… avg=… min=… max=…` updates live as the user drags out a multi-cell selection. Walks the selection's numeric cells (stock / min / sell / cost / total fields), ignores text cells like model names so the average isn't polluted. Hidden for single-cell selection.
- Both the filter and selection stats survive a refresh — `_attach_selection_handlers()` and `_apply_row_filter()` run after every `_apply_refresh`, so a brand-combo change or admin save doesn't lose the user's current filter.
- Implementation: filter only sets row-hidden flags (no widget rebuild — ~1 ms even on a 200-row table); `MatrixWidget.selection_stats()` walks `selectedItems` and pulls displayed values from each cell's `meta` dict.

### Added — Transactions page auto-refresh
- **Transactions history now polls itself every 30 seconds** while the page is visible, so a user who leaves the app open all day still sees recent stock operations land without manually clicking the refresh button. Stops when the user navigates away (saves the DB round-trip every 30 s for as long as they're on a different page) and fires once immediately on `showEvent` so the first paint after a long background period isn't stale.
- **Doesn't disrupt browsing**: the tick is a no-op if `self._offset > 0` (the user clicked "Load more" to view older transactions) OR the vertical scrollbar is more than half a row off the top — both signal active inspection that a silent reload would pull the user away from. Idle users at the top get fresh data; busy users at row 200 keep their place.
- Implementation: `QTimer` parented to the page, started/stopped in `showEvent` / `hideEvent`. Tick calls the existing `_apply_filters` which already runs through the worker pool (debounced by key, async) so the auto-refresh costs nothing on the UI thread.

### Added — Power-user keyboard shortcuts
- **Ctrl+F** — focus the search box from anywhere on the matrix tab. Standard "find" muscle memory.
- **Ctrl+0** / **Ctrl+L** / **Ctrl+O** / **Ctrl+R** — switch to the All / Low / Out / Reorder chip.
- **Esc** in the search box clears the filter (back to no-text).
- **Enter** in the search box applies the filter immediately (skips the 150 ms debounce).

### Fixed
- **Matrix scroll position fully preserved across stock edits — no movement at all.** The earlier draft re-centered the edited model's row via `scrollToItem(..., PositionAtCenter)`; the user wanted absolute zero movement. Removed the `_scroll_to_saved_model` helper entirely and now rely solely on the legacy pixel-exact `_post_apply_refresh` restore (saves the scrollbar's pixel offset before refresh, schedules retried `setValue(target)` via `QTimer` so the layout-timing race against rebuilt rows is handled gracefully). Result: stock edit completes, viewport stays at the exact same Y offset.
- **Removed the pre-filter `clearSelection()` + `setCurrentCell(-1, -1)` calls** I had added for crash hardening — they were the proximate cause of the original "jump to top" bug because Qt scrolls the viewport when the current cell is reset. Only the lightweight `_hover_row` Python attribute reset survives now (no Qt-side effect, no scroll jump).
- **Stack-of-stripes when filter narrows results** — when the user filtered to non-adjacent series (e.g. `Reorder` showing iPhone 11 Pro and 13 Pro max with the entire 12 series hidden between them), my earlier draft showed BOTH the 11→12 boundary AND the 12→13 boundary as separate 3 px stripes back-to-back. Now collapses to **at most ONE separator** between any two consecutive visible models — multi-separator gaps stay hidden because crossing multiple skipped series is itself the visual cue, no need to add divider noise on top.
- **`UnboundLocalError: cannot access local variable 'QToolButton'`** on Matrix tab construction — caused by an inner `from PyQt6.QtWidgets import QToolButton` inside `MatrixTab.__init__` that, due to Python's function-scope rule, made every `QToolButton` reference in the function local even though the use at line 175 came earlier. Moved `QButtonGroup` / `QTimer` to the module-top imports and dropped the redundant inner imports.
- **Crash on filter** caused by stale current-cell selection landing on a now-hidden row — Qt's `currentCellChanged` signal fires when the current row is hidden, which can cascade into hover-delegate paths that don't expect to be repainted at that moment. `_apply_row_filter` now clears every container's selection AND resets the hover-row index BEFORE running `filter_rows`, then triggers a viewport repaint to flush any stale hover ghost. Defensive `RuntimeError` guards everywhere so the timer-driven walk survives a tab navigation that destroys widgets mid-iteration.
- Quick-filter chips, Σ stats label, and match-count label all re-style themselves on theme toggle via `MatrixTab.apply_theme`.

### Performance
- **`setUpdatesEnabled(False)` wrapper** around the row-hide loop in `FrozenMatrixContainer.filter_rows` — flushes ONE final repaint at the end instead of N during the walk. Verified: 100 filter operations across 3 brand containers (500+ total rows) complete in 858 ms total = ~9 ms per operation. Fast typing in the search box feels instant; no per-keystroke flicker even on the 376-row Samsung container.
- Stress test: 50 random fuzz iterations (random query strings + random chip switches) → **zero exceptions, zero crashes**.

## [2.4.9] - 2026-04-29

Big release bundling barcode-generator overhaul, performance round 1+2, comprehensive theme-system fix, and a new scan-action popup. Each section below is self-contained — read the bits relevant to what you're touching.

### Added — Scan-action popup
- **Header-bar barcode scan now opens a `ScanActionDialog` for known items** instead of navigating to the inventory page and selecting the row. The popup shows item identity (display name, barcode in monospace, stock/min/price stat cards) plus a colour-coded status badge (`IN STOCK` / `LOW STOCK` / `OUT OF STOCK`) so a shop assistant can read the state from across the room. Three primary action buttons close the dialog with the matching signal — **Stock In** (green), **Stock Out** (red), **Adjust** (orange, exact-value entry) — wired to the same `stock_ops.ctx_stock_op` controller every other entry point uses, so the qty-entry / undo-push / summary-refresh chain stays consistent. Secondary row: **Edit** (opens the existing edit dialog) and **Cancel**. Default focus on **Stock In** — most common op when scanning incoming inventory from a delivery.
- **Unknown-barcode flow preserved** — still asks "Add new product?" with the scanned barcode pre-filled. Only known-item scans switch to the popup.

### Added — Barcode Generator
- **Per-color direct-scan barcodes** (`BRAND-MODEL-PT-COLOR`, e.g. `SA-S22U-DSP-BK`) alongside the legacy two-step "scan model -> scan colour" flow. Both coexist; user picks per-batch via the new "Include per-color barcodes (direct scan)" checkbox. `BarcodeEntry` carries a `color` field; `ScanSession.process_barcode` short-circuits the wait-for-colour state when a colour barcode resolves directly to a coloured row.
- **Brand filter combo + live "X items match" count** on the Barcode Generator page. Brand narrows every scope (All / Category / Model / Part Type). Count is a single `COUNT(*)` (`ItemRepository.count_items_for_scope`) recomputed on every filter change.
- **"Regenerate (overwrite existing)" checkbox** — recomputes saved codes from current model + part-type names. Useful after renaming a part type ("ORG-Service-Pack-SM" -> "ORG Service Pack" leaves saved codes stuck on the old name; tick this and Generate to refresh). Implies "Include items with existing barcodes" — auto-ticks and locks the dependency.
- **Model picker auto-narrows to the selected brand** — by-model scope no longer scrolls through 100 mixed-brand models when a brand is chosen.

### Changed — Barcode Generator
- **Async generation pipeline split into Stage 1 / Stage 2**:
  - Stage 1 (DB fetch + entries, ~300 ms) runs on Generate; lights up Assign & Save and Export for YunPrint immediately.
  - Stage 2 (PDF assembly via fpdf2 + PyMuPDF preview rasterisation, 20-30 s on a 2000-item batch) only runs on first Export PDF / Print click.
  - YunPrint export workflow (`Generate -> Export for YunPrint -> drop into YunPrint Database`) is now ~1 s end-to-end instead of ~30 s. The PDF was rendered eagerly even when the user only wanted the .txt.
- **Professional encoding across all brands**. Legacy `X-NOTE1-SMOR-SV12` -> new `XI-NOTE14P+-OSP-SV`:
  - Brand: 2-letter codes via `_BRAND_SHORT` (Apple->IP, Samsung->SA, Xiaomi->XI, Redmi->RD, Huawei->HW, Honor->HO, OPPO->OP, Vivo->VI, Realme->RM, OnePlus->1+, Google->GO, Nokia->NO, Motorola->MO, Sony->SO, LG->LG). Two-letter fallback for unknown brands.
  - Model: `_abbreviate` max_len 5 -> 8; word map gains `PRO+`->`P+`, `LITE`/`FOLD`/`FLIP`/`EDGE`/`NEO`. "Note 14 Pro+" -> `NOTE14P+` instead of truncated `NOTE1`. Strips additional brand-line prefixes (`POCO `, `MI `, `PIXEL `, `HONOR `, `NOTHING `).
  - Part type: new `_part_type_code` extracts parenthesised tags as prefix (`(JK)`->`JK`, `(D.D)`->`DD`) and uses word initials for the rest (`ORG Service Pack`->`OSP`, `(JK) incell FHD`->`JKIF`). Single-word PTs get first 4 letters so "Battery"->`BATT`.
  - Collision suffix: `f"{base}-{suffix}"` separator (`...-SV-2` instead of glued `...-SV2` that read as "Silver-2").
  - **Affects new barcodes only**. Existing items keep saved codes unless the new Regenerate checkbox is ticked.
- **YunPrint export format**: `.txt` with RFC-4180 CSV (UTF-8 BOM, `csv.writer` `QUOTE_MINIMAL`). YunPrint's Excel importer silently rejected openpyxl `.xlsx`; tab-TSV was read as one oversized column because YunPrint's segmentation defaults to comma.

### Performance — Database
- **4 hot-path indexes via V17 -> V18 migration**: `phone_models(brand)`, `part_type_colors(part_type_id)`, `model_part_type_colors(model_id, part_type_id)` composite, `inventory_transactions(item_id, timestamp DESC)` covering. `ANALYZE` after migration so the planner picks them up immediately. Indexes also baked into the DDL for fresh installs.
- **`_ensure_all_entries` smart-skip via fingerprint** (`_matrix_fingerprint`): hashes (count, max(updated_at)) over the 5 contributing tables, cached in `app_config.matrix_fingerprint`. Idempotent calls drop **221 ms -> 0.08 ms (2700x)**. Saves ~200 ms on every startup and admin-save where nothing actually changed.
- **`_ensure_all_entries` batched DELETEs**: pre-fetch stale-colour candidates once, queue IDs, flush as one `DELETE ... WHERE id IN (?, ...)` chunked at 500 IDs. Cleanup pass at the end uses `executemany` instead of N round-trips.
- **`bulk_update_barcodes` -> `executemany`**: one round-trip per batch instead of one per row (~50x on 100-item batches).
- **PRAGMA tuning**: `cache_size` 20 MB -> 32 MB, new `mmap_size = 128 MB` so SQLite memory-maps the DB on read-heavy paths.
- **`InventoryItem` -> `@dataclass(slots=True)`**: ~40 % per-instance memory drop, marginally faster attribute access. Real win on the inventory page where 2871 items are materialised every refresh.
- **`reorder` methods** (`ModelRepository.reorder`, `CategoryRepository.reorder` / `reorder_part_types`) switched to `executemany` — was per-row UPDATE inside a Python loop.

### Performance — Repositories
- **Process-wide caches** for the read-mostly methods called dozens of times per session:
  - `ModelRepository.get_brands()`: 300 us -> **0.4 us cached (750x)**. Invalidated by `add` / `delete` / `rename` / `reorder`.
  - `CategoryRepository.get_all_active()`: ~5 ms -> **0.3 us cached (15000x)**. Invalidated by 10 mutation methods (categories + part types + colours). The single biggest win on page-switch latency since every category combo hits this.
  - Both caches use a `threading.Lock` (worker threads read concurrently with UI-thread mutations) and return defensive copies so callers can't poison the cache.

### Performance — UI
- **Barcode generation runs on the worker pool** instead of the UI thread. The legacy `_generate` chain (DB fetch -> image render -> PDF assemble -> preview rasterise) all blocked the UI thread; a 2000-item category froze the app for 30-60 s. Now the user keeps using the app while it runs.
- **Matrix widget zoom path**:
  - Stop concatenating QSS (`mtx.setStyleSheet(self.styleSheet() + body_qss)` made the rule blob grow on every zoom). Replace, don't append.
  - Cap data-cell font-metrics measurement to a 100-row sample (was every row x every column = ~7000 calls per zoom).
  - Skip no-op `setRowHeight` calls (every Qt setRowHeight triggers a layout invalidation even when the height didn't change).
- **Matrix tab models filter**: items unchecked in Part Type Settings are removed from the matrix entirely instead of leaving "disabled" empty rows. `ItemRepository.get_matrix_items` filters out `(model, pt)` combos with the `__EXCLUDED__` marker; matrix tab also drops models that have no remaining items in any displayed part type.

### Fixed — Theme System
- **`ThemeManager` promoted to `QObject` with a `changed` signal**. The legacy `set_theme` only re-applied QSS to `_targets[0]`, leaving every other registered widget (dialogs, popups, settings panels) silently ignored. Now applies to the full `_targets` list AND emits `changed` so widgets that captured `tk.tX` colours at construction can re-read from `THEME.tokens` and refresh.
- **`MainWindow._refresh_theme`** connected once to `THEME.changed`. Walks the widget tree from the main window root, calls `apply_theme()` on every descendant that defines one (lazy-loaded pages too — `findChildren(QWidget)` reaches them through their stack-widget parent), targeted polish on sidebar / header / footer (which use dynamic-property selectors that need explicit re-polish). Replaces the legacy manual fan-out in `_toggle_mode` so every code path that switches themes (toggle button, admin Settings dialog, programmatic API) goes through the same single refresh.
- **`THEME.warm_cache()` scheduled on idle** after `window.show()` — pre-generates QSS for all four themes (`pro_dark` / `pro_light` / `dark` / `light`) so the first toggle dispatches in **< 1 ms** instead of paying ~80 ms to build the QSS string.
- **`apply_theme()` added to widgets that bake `tk.X` colours at construction**, discovered automatically by the widget-tree walk:
  - `LanguageSwitcher._TriggerButton` — pill background / border / label colours.
  - `MatrixWidget` — brand-header rows + separator rows tracked at load, repainted in place via `setBackground` (~1 ms vs ~100 ms full rebuild).
  - `MatrixTab` — full re-render against the cached worker payload (`self._last_payload`). Rebuilds KPI cards, brand-section header QLabels in the all-brands view, every data cell. No DB hit. Eye icon (cost-mode toggle) re-applies `_apply_cost_toggle_style` with current `COST_VIS.visible` state.
  - All-brands view's brand-section header `QLabel` (built by `_add_brand_section`) gets a closure-based `apply_theme` attribute that rebuilds its inline stylesheet against current tokens.
  - `ProductDetailBar` — 17 inline styles refactored into a single `_apply_styles()` method called from both `_build()` and `apply_theme()`. Local headers + separators saved as `self.*` so the refresh path can reach them.
  - `SummaryCard` — every standalone instance is now self-refreshing (was previously refreshable only via `DashboardWidget`'s private `_cards` dict, so KPI tiles owned by Audit / Reports / etc. stayed stuck).
  - `AuditListView` — title / subtitle labels saved as `self.*` and refreshed via a centralised `_apply_header_styles`.
  - `PivotTable` (Valuation Pivot) — re-runs `_render()` against cached `self._data`, covering all four sub-classes' 46 inline-style call sites in one pass.

### Fixed — Other
- **Barcode lookup survives scanner-mark prefix differences**. Pre-V17 the system hardcoded a leading `f` on every saved barcode; real-world testing on the K30F + YunPrint combo emitted `a` instead. Now the DB stores barcodes canonically (no prefix) and lookup paths strip whatever lowercase prefix the scanner emits before matching, via `normalize_barcode()`. V16 -> V17 migration strips legacy prefixes from `inventory_items.barcode` and `app_config.value` (for `scan_cmd_*` / `scan_clr_*` keys).
- **Part-type panel Models & Colours table shows every brand by default**, not just the alphabetically-first one. New Brand: dropdown above the table; brand-header rows separate each brand's models in "All brands" mode. Auto-detect-by-most-items SQL removed.
- **`requirements.txt`** declares `openpyxl==3.1.5` explicitly (already imported by `export_service.py` / `import_service.py` but missing from the file, so fresh installs / PyInstaller builds were missing it).

### Removed
- Legacy manual `unpolish/polish` fan-out in `_toggle_mode` (eight separate loops). Replaced by the single signal-driven walk in `_refresh_theme`.

## [2.4.8] - 2026-04-28

### Fixed
- **Barcode lookup now survives scanner-mark prefix differences** — pre-V17 the system hardcoded a leading lowercase ``f`` on every saved barcode (e.g. ``fAß11PMßJKIN``) because that's what the original developer's German-keyboard scanner emitted as a "scanner mark" before each scan. Real-world testing on the K30F + YunPrint combo revealed the scanner emits a *different* lowercase letter (``a``) when reading YunPrint-rendered Code 39 instead of python-barcode-rendered Code 39, so DB lookups against ``f...`` rows missed every scan from a YunPrint-printed label. Going forward the DB stores barcodes in their canonical (prefix-less) form and lookups strip whatever lowercase letter the scanner happens to emit, so old PDF prints, new YunPrint prints, and any future renderer all match the same DB row.
  - New `normalize_barcode()` helper in `barcode_gen_service.py` — strips a single leading ASCII a-z when followed by an uppercase letter or digit (canonical payloads always start with brand letter / digit, never another lowercase letter, so the rule is unambiguous). Idempotent.
  - `_barcode_for_db()` no longer prepends ``f`` — returns the canonical (prefix-less) form.
  - `_to_code39()` uses `normalize_barcode()` so it accepts ``f...``, ``a...``, or no-prefix input identically.
  - `ItemRepository.get_by_barcode()` normalises input before the DB query.
  - `ScanConfig.is_command()`, `command_type()`, `is_color_barcode()`, `color_name()` all normalise both sides of the comparison so command/color barcodes also stop caring which scanner mark the hardware emits today.
- **Schema migration V16 → V17 — strip scanner-mark prefix from existing rows.** Updates `inventory_items.barcode` and `app_config.value` (for `scan_cmd_*` and `scan_clr_*` keys) to drop a leading lowercase letter when followed by an uppercase or digit. Runs once on first launch after upgrade. Heuristic-safe — only touches rows that match the scanner-mark pattern and leaves anything else untouched.

## [2.4.7] - 2026-04-28

### Fixed
- **YunPrint export format — switched from `.xlsx` to RFC-4180 CSV (`.txt`)** so YunPrint's Database dialog actually parses the file. The 2.4.5 implementation wrote an openpyxl `.xlsx` and instructed the user to import via Excel mode; live testing on the K30F revealed YunPrint's Excel parser silently rejects openpyxl-generated workbooks (Sample-data preview empty, field-binding dropdown empty), and the tab-delimited fallback was read as a single oversized column because YunPrint's `.txt` mode defaults to `Character Segmentation: Comma` and doesn't auto-detect tabs. Final format is comma-separated, UTF-8-BOM, written via Python's `csv.writer` with `QUOTE_MINIMAL` — YunPrint parses out the six columns (`barcode`, `model`, `part_type`, `model_full`, `brand`, `label`) cleanly and the user can bind each template field to a single column from the dropdown.
  - File extension stays `.txt` (matches the YunPrint Database mode that actually works on the K30F + Dlabel driver combo).
  - The how-to dialog shown after export now reflects the `.txt` Database mode flow rather than the broken Excel mode flow.
  - `openpyxl` import is removed from `BarcodeGenService.export_for_yunprint`. The dep stays in `requirements.txt` because `export_service.py` and `import_service.py` still use it for general Excel I/O.

## [2.4.6] - 2026-04-28

### Fixed
- **Part Type Settings — Models & Colors table now shows every brand, not just one.** Previously, when selecting a part type (especially a brand-new one with no inventory yet), the table only displayed models from a single auto-detected brand: the brand with the most existing items, or — for a fresh part type — the brand that came first alphabetically. Every other brand was invisible, so users couldn't tick/untick across the full catalogue without dropping to the database.
  - Default scope is now **All brands**, with brand-header rows separating each brand's models in the table.
  - New **Brand:** dropdown (All brands · Apple · Samsung · …) at the top of the Models & Colors card lets the user narrow the scope when a single brand has too many models. Selection is preserved across part-type changes within the same session.
  - Brand-header rows use the existing `model_id == -1` placeholder convention, so the include/exclude checkbox handler and double-click color-edit handler skip them automatically — no risk of accidentally toggling/editing a header.
  - The auto-detect-by-most-items logic that picked a single brand has been removed entirely; the user is in control via the dropdown.

## [2.4.5] - 2026-04-27

### Added
- **Export for YunPrint (K30F label printer support)** — new "Export for YunPrint" button on the Barcode Generator page. Generates an `.xlsx` workbook one-row-per-barcode that YunPrint/Dlabel can import via its **Database** dialog (Excel mode, "first line contains the field name"). Once a 50×20mm template is designed once with template fields bound to `Database`, every future batch is: Generate → Export for YunPrint → in YunPrint click Database → pick the file → Print all. One print job for the whole batch — no per-label clicking.
  - **Same Code39 strings** already saved on items go straight into the `barcode` column, so labels printed by the K30F scan identically to the existing app barcodes — no regeneration, no migration.
  - Columns exported: `barcode`, `model` (compact brand-prefixed form like "IP 11 Pro Max" / "SA S25 Ultra"), `part_type`, `model_full` (full original "iPhone 11 Pro Max"), `brand`, `label`. The user picks whichever fits their template.
  - Brand short codes (`IP`/`SA`/`XI`/`HW`/...) live in `_BRAND_SHORT` in `barcode_gen_service.py` with a 2-letter fallback for unknown brands.
  - Skips command/color scanner barcodes — those are scanner-only and don't belong on per-item stickers.
  - After save, opens the containing folder in Explorer and shows a one-shot how-to dialog so the user knows the YunPrint import flow without leaving the app.
  - Reuses the existing scope selector on the Barcode Generator page (All / Category / Model / Part Type) — same scope produces the YunPrint xlsx and the legacy A4 PDF.

### Changed
- **`requirements.txt`** — declares `openpyxl==3.1.5` explicitly. The dep was already imported by `export_service.py` and `import_service.py` but had been missing from the requirements file, so fresh venvs / PyInstaller builds were missing it. The new YunPrint export uses it too. No runtime change for environments where it was already installed transitively.

## [2.4.4] - 2026-04-27

### Fixed
- **Part Type Settings — unchecking a model now removes it from the matrix instead of leaving a "disabled" empty row.** Previously, unchecking a model in Admin → Part Types only set an `__EXCLUDED__` marker in `model_part_type_colors` and pruned zero-stock inventory rows; rows with stock/min_stock/inventur stayed in the DB and continued to render in the matrix as "—" cells, producing a confusing half-removed look.
  - `ItemRepository.get_matrix_items` now joins against `model_part_type_colors` with a `NOT EXISTS` filter, so any (model, part_type) combo carrying the `__EXCLUDED__` marker is dropped from the result regardless of stock state. Existing data is preserved — re-checking the model in Part Type Settings restores the rows exactly as before.
  - `MatrixTab._apply_refresh`, `_add_brand_section`, and `_reload_brand_container` now filter the `models` list to only those that have at least one item left in `item_map`. A model that has been excluded from every part type its brand previously had inventory in vanishes from the matrix entirely instead of rendering as an empty row.

## [2.4.2] - 2026-04-21


## [2.4.2] - 2026-04-21

### Added
- **Shop setting: "Show sell totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under UI Scale). When off, the matrix TOTAL column and the value portion of the per-part-type cards + the grand-total card are hidden, so shop assistants see stock counts without seeing sell valuation. Units stay visible either way. Cost mode (PIN-gated via 👁) overrides the hide so the cost/sell comparison still makes sense when the owner has authenticated.
  - Persisted via `ShopConfig.show_sell_totals` (reuses the existing `app_config` key-value mechanism — no DB migration needed).
  - Typed accessor `ShopConfig.is_show_sell_totals`.
  - Default is ON — existing users see zero change until they toggle it off.
  - Live-update on Save: the existing settings-close rebuild chain (`ShopConfig.invalidate()` → `rebuild_matrix_tabs()` fast path → `tab.refresh()`) propagates the new state to every matrix tab instantly.

### Fixed
- **Float-precision display bug** — `7 × 22.99` was rendering as `€160.9299999999998` in matrix TOTAL cells and cards. `ShopConfig.format_currency` used `str(amount)` which exposed the full Python-float representation. Now formats with `f"{float(amount):,.2f}"` — always exactly 2 decimals, thousands separator included. One-line fix at source means every money display across the whole app (matrix cells, cards, Quick Scan, Sales, POS, Analytics, Reports, Purchase Orders) benefits automatically.

---

## [2.4.0] - 2026-04-21

### Added
#### Lazy UI construction — startup & settings-close no longer freeze

- **`NavController.register_lazy(key, page_index, factory, on_activate)`** — new API. The factory runs on first navigation; a lightweight `QWidget` placeholder holds the stack slot until then. `register_placeholder(page_index)` + `realize(key)` + `get_lazy_instance(key)` complete the contract.
- **`_MatrixPlaceholder`** — matrix category tabs are now placeholders until the user clicks their sidebar entry. On first click `NavController._go_matrix` swaps the placeholder for a real `MatrixTab` in the same stack slot, emits `navigated`, then kicks the first `refresh()` via `QTimer.singleShot(0, …)` so the switch paints before the DB round-trip lands.
- **10 static pages migrated to lazy**: `SalesPage`, `CustomersPanel`, `PurchaseOrdersPage`, `ReturnsPage`, `BarcodeGenPage`, `ReportsPage`, `SuppliersPage`, `AnalyticsPage`, `AuditPage`, `PriceListsPage`. Each has a closure-style factory that sets `self._xxx_page` before returning; the `AnalyticsPage` factory also wires `navigate_to.connect(nav_ctrl.go)` after construction. Eager pages (`InventoryPage`, `TransactionsPage`, `QuickScanTab`) stay immediate.
- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract for pages/tabs: `self.async_refresh(fetch, apply, key_suffix, debounce_ms)`. Keyed cancellation, `_is_alive()` guard using `sip.isdeleted`, error-path falls through to a non-blocking `_show_empty_state` instead of a modal. Baked into `BaseTab` so every matrix tab inherits it.
- **UI-thread watchdog** (new `app/ui/workers/ui_watchdog.py`) — opt-in via `SM_UI_WATCHDOG=1`. A 10 ms `QTimer` stamps `time.monotonic()`; a daemon thread warns whenever the main thread hasn't heartbeat in > 50 ms. Zero cost when disabled. Regressions that put sync DB calls back on the UI thread show up instantly in the logs.
- **Grand-total card** at the end of the matrix cards strip — emerald-accent anchor showing total units and total valuation across every part-type in the current filter. Metric tag flips `sell` ↔ `cost` with the admin toggle, exactly like the per-part-type cards.

### Performance

- **Worker pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result / error callbacks are gated by the captured epoch so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - `POOL.has_pending(key)` helper so callers can coordinate with in-flight critical workers.
  - `POOL.shutdown(timeout_ms)` — called from `MainWindow.closeEvent`; cancels all work, stops debounce timers, `waitForDone()` the underlying `QThreadPool`. No more leaked workers on exit.
  - Callback error containment: exceptions inside `on_result` / `on_error` are logged instead of silently killing the signal chain.

- **Settings-close freeze — fully resolved.** `ensure_matrix_entries` (can touch 1000+ rows) now runs on `POOL` keyed `"admin:matrix_ensure"`. The admin dialog returns **instantly**. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs` → fast-path, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`). `on_error` fallback still rebuilds so the user never gets a stuck UI on a DB hiccup.

- **`rebuild_matrix_tabs` fast path** — if the active-category set hasn't changed (the common case on settings close), existing realised tabs are KEPT intact and just marked `_dirty=True`; the currently-visible tab gets a refresh via `QTimer.singleShot(0, …)`. Previously rebuild unconditionally nuked every realised tab into a placeholder, leaving the user looking at an empty page for a moment. Only true category adds/removes/reorders take the slow path and recreate placeholders.

- **`MatrixTab.refresh()`** fully async — every DB query (`get_matrix_items`, `get_all`, `get_brands`) runs off the UI thread via `POOL.submit`. In all-brands mode this replaced up to 12 synchronous repo hits per refresh with one pooled fetch; the UI thread no longer touches the DB during brand-combo changes, cost-toggle flips, or post-edit refreshes. `_add_brand_section` / `_reload_brand_container` accept pre-fetched `models=` / `item_map=` kwargs so the worker feeds every brand section at once.

- **Matrix lazy refresh** — per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between tabs. Each tab has a `_dirty` flag; on `COST_VIS.changed`, only the currently visible tab refreshes immediately, others flip `_dirty=True` and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries every time the 👁 button is clicked.

- **`ProductTable.load()`** — replaced per-row `setRowHeight(i, 48)` loop with a single pre-loop `verticalHeader().setDefaultSectionSize(48)`. The per-row call triggered a layout recalc even with `setUpdatesEnabled(False)` — saves 400-600 ms of startup UI-thread work for a 300-item inventory.

- **Per-page async conversions** —
  - `SalesPage._load_products` + `_refresh` split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` combined `po_repo.get_all` + `po_repo.get_summary` into one `POOL.submit_debounced("po_refresh", …, 150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` combined `get_all_audits` + `get_summary` into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **`AnalyticsPage.__init__`** — inline `self.refresh()` deferred via `QTimer.singleShot(0, self.refresh)` so widget-tree construction completes before the skeleton paint + 5 POOL workers fire. Combined with lazy construction, analytics costs nothing until the user actually opens the page.

- **`StartupController._on_ok`** — removed the eager `analytics_page.refresh()` call now that analytics is lazy. Saved 200-400 ms of skeleton-paint + worker dispatch at startup for a page the user may never open.

### Fixed

- **Blank matrix tab after settings close** — root cause was a `POOL.has_pending("admin:matrix_ensure")` guard inside `MatrixTab.refresh()`. Qt dispatches slots in connection order, so user callbacks fire **before** the pool's own `_cleanup` slot; the guard incorrectly returned `True` inside the very callback that was triggered by result delivery. Guard removed (WAL handles concurrent reads safely); the fast-path `refresh()` in `rebuild_matrix_tabs` is now deferred via `QTimer.singleShot(0, …)` so it runs on a clean event-loop idle tick.
- **Silent matrix refresh failures** — `MatrixTab.refresh()`'s `POOL.submit` now has an `on_error` handler that logs the failure with the category key. No more invisible worker exceptions leaving a page blank.
- **`ProductTable.setRowHeight` in loop** — per-row call triggered layout recalcs that `setUpdatesEnabled(False)` couldn't suppress. Moved to `defaultSectionSize` once before the loop.

### Changed

- Matrix staggering experiment reverted — staggering brand sections across ticks via `QTimer.singleShot(0, …)` opened race windows where a second refresh mid-chain left the page blank. Correctness > 200 ms of visual smoothness: `_apply_refresh` builds all sections inline.
- `MainWindow.closeEvent` now calls `POOL.shutdown(2000)` for graceful worker drain.

---

## [2.3.10] - 2026-04-21

### Added
#### Cost valuation — PIN-gated matrix redesign
- **`cost_price` column** on `inventory_items` — purchase / buy price, persisted per item. Schema V16 migration adds the column automatically on first launch.
- **Matrix columns bumped 5 → 7** per part-type group: `MIN-STOCK · DIFFERENCE · STOCK · ORDER · SELL · COST · TOTAL`.
  - **SELL** = the previous "PRICE" column renamed for clarity (item.sell_price with part-type default fallback; edit flow unchanged).
  - **COST** = new, shows `item.cost_price` in the shop's accent blue. **Hidden by default** — only shown after the owner toggles it.
  - **TOTAL** = always visible. Metric flips with the cost toggle:
    - Default: `stock × effective_sell_price`
    - Admin mode: `stock × cost_price`
  - Cell tooltip clarifies which metric is active ("Stock × sell = …" / "Stock × cost = …").
- **👁 cost-visibility toggle** in every matrix tab toolbar. Click prompts for `ShopConfig.admin_pin` (if configured, via `QInputDialog` password-echo — same pattern as `open_admin`). Button swaps closed-eye ↔ talking-eye icon and shows a green accent border when active. One flip fans out to every matrix tab via `CostVisibility.changed`.
- **Professional per-part-type cards** at the top of every matrix tab (name · total units · total valuation · `sell`/`cost` suffix). Live metric — switches from sell-based → cost-based totals when the toggle is on. Card strip lives inside a restored collapsible `BRAND & LEGEND` section alongside the brand filter row.
- **Editable cost_price** — double-click a COST cell (admin mode only) opens the same numeric dialog pattern used for sell; full Undo/Redo via `ItemRepository.update_cost_price()`.
- **Currency symbol everywhere** — SELL, COST, TOTAL cells + tooltips format through a new `_fmt_money()` helper backed by `ShopConfig.format_currency()`.

### New services / repos
- `app/services/cost_visibility.py` — session-local `COST_VIS` singleton (`QObject` with `changed` signal). Default `visible=False` on every app start — nothing persists, so sensitive valuation never leaks on an unattended laptop.
- `ItemRepository.update_cost_price(item_id, new_cost)` — new write method; `_build()` reads `cost_price` when the column exists.
- `_type_visible_width(table, ti)` helper in `matrix_widget.py` — sum of *visible* column widths for a part-type group, so banner chips never over-stretch when the COST column is hidden.
- `_SUB_MIN / _SUB_BB / _SUB_STOCK / _SUB_ORDER / _SUB_SELL / _SUB_PRICE / _SUB_TOTAL` sub-column constants — arithmetic across the matrix now self-documents.

### Performance — professional worker-pool overhaul

- **Pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result and error callbacks are gated by the captured epoch, so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - New `POOL.has_pending(key)` helper so callers can skip a refresh while a critical worker (e.g. `admin:matrix_ensure`) is still writing.
  - New `POOL.shutdown(timeout_ms)` that cancels everything, stops debounce timers, and `waitForDone()` the underlying `QThreadPool`. Called from `MainWindow.closeEvent` — no more leaked workers on exit.
  - Callback-error containment: exceptions inside `on_result` / `on_error` handlers are now logged instead of swallowing the signal stream.

- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract every page/tab now follows:
  - `self.async_refresh(fetch=…, apply=…, key_suffix=…, debounce_ms=…)`
  - Auto-cancels prior task via `POOL` keyed as `f"{POOL_KEY_PREFIX}:{key_suffix}"`.
  - `_is_alive()` guard using `sip.isdeleted` so callbacks skip deleted widgets (tab closed mid-load, language rebuild, etc.).
  - Error path falls through to `_show_empty_state(msg)` inline, not a modal — no more freezing on an error dialog.
  - Baked into `BaseTab` so every matrix tab and future tab gets it for free.

- **Startup freeze — resolved** —
  - `MainWindow._build_ui` defers `rebuild_matrix_tabs()` via `QTimer.singleShot(0, …)`; the main window paints and becomes interactive before any DB work.
  - On first-run setup, `ensure_matrix_entries()` (can touch 1000+ rows) runs on a `POOL` worker; the widget rebuild runs in the `on_result` callback on the main thread.

- **Settings-close freeze — resolved** —
  - Admin-dialog close now submits `ensure_matrix_entries` to `POOL` keyed `"admin:matrix_ensure"`. The dialog returns instantly. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs`, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`).
  - `on_error` fallback still rebuilds tabs so the user never gets a stuck UI on a DB hiccup.
  - `MatrixTab.refresh()` early-returns when `POOL.has_pending("admin:matrix_ensure")` — prevents mid-write reads and sets `_dirty=True` so the tab reconciles on its next `showEvent`.

- **Matrix lazy refresh** —
  - Every `MatrixTab` now has a `_dirty` flag. On `COST_VIS.changed`, only the **currently visible** tab refreshes immediately; others flip the flag and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries when the 👁 button is clicked.
  - Each `MatrixTab` uses a per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between parallel tabs.

- **Per-page migrations off the UI thread** —
  - `SalesPage._load_products` + `SalesPage._refresh` — both split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` — `po_repo.get_all` + `po_repo.get_summary` combined into a single `POOL.submit_debounced("po_refresh", …, delay_ms=150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` — `get_all_audits` + `get_summary` combined into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **UI watchdog** (new `app/ui/workers/ui_watchdog.py`) —
  - Opt-in dev diagnostic enabled via `SM_UI_WATCHDOG=1`.
  - A 10 ms `QTimer` on the UI thread stamps `time.monotonic()`; a daemon thread polls every 50 ms and logs a warning whenever the stamp is older than a configurable threshold (default 50 ms). Instantly surfaces any regression that puts a sync DB call back on the UI thread.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Changed
- Matrix edit dialogs for price split into **Sell Price** and **Cost Price** with distinct titles / Undo labels.
- Cost edit instant-repaints the clicked COST cell + neighbouring TOTAL cell synchronously before the DB refresh lands, so the whole edit lands in a single visual frame. SELL edit does the same for TOTAL when not in cost mode.
- Schema version bumped **15 → 16**.

---

## [2.3.9] - 2026-04-20

### Added
#### Pricing · Quick Scan · Invoices
- **Part-type default price** — Admin → Part Types now has a "Default price" field. Every item inheriting the part type takes that price; per-item `sell_price` still overrides. New "PRICE" column in the part-type admin table.
- **€ / Price column in the matrix** — new column per part type. Green when a per-item override exists, grey when falling back to the part-type default. Double-click to edit; Ctrl+Z undoes.
- **Quick Scan live pricing & totals** — pending table now shows **Unit Price** and **Line Total** per scanned line + a totals card with **ITEMS · SUBTOTAL · GRAND TOTAL** (accent green, JetBrains Mono). Currency formatted via `ShopConfig.format_currency`.
- **Customer field on Quick Scan** — optional input; printed on the invoice when present, otherwise a walk-in record.
- **PDF invoices on every commit** — confirming a scan asks **A4 invoice** or **Thermal receipt**, persists the header + line items, and writes to `%LOCALAPPDATA%\StockPro\StockManagerPro\invoices\INV-YYYYMMDD-NNNN.pdf`. Feed row shows an **Open** button. TAKEOUT → "INVOICE"; INSERT → "STOCK RECEIPT". Layout preference remembered via QSettings.
- **New `ScanInvoiceService`** (A4 + 80 mm thermal fpdf2 layouts) and **`InvoiceRepository`** (day-prefixed numbering + price snapshot per line).

#### Reports — full overhaul
- **5 new reports**: Stock Valuation (per part type, category subtotals, grand total), Sales (with top-10 best sellers), Scan Invoices (IN/OUT history with filter), Expiring Stock (urgency-coloured), Category Performance (stock + movement per category).
- **Inventory report** now groups by **Category → Part Type** with per-section subtotals, a Brand column, and a grand-total emerald bar at the end.
- **Date range picker** on the reports page — presets (Today · 7d · 30d · 90d · This year · Custom) + `QDateEdit` from/to pickers. Applied to every date-aware report.
- **Operation filter** — contextual for Transactions (IN/OUT/ADJUST/CREATE) and Scan Invoices (ALL/IN/OUT).
- **Output path + three actions** — status bar shows the saved PDF path with **Open PDF**, **Open folder** (selects file in Explorer), **Copy path**.
- **`_ReportPDF.header() / footer()` overrides** — shop banner, title subtitle, and `Page X of Y` footer render on **every page** (not just page 1) via `alias_nb_pages()`.
- **Logo support** — `ShopConfig.logo_path` is rendered top-left of every report header when the file exists.
- **Per-table pagination** — every table redraws its column headers on a new page when rows cross the bottom margin.

#### Analytics — professional dashboard
- **Top date-range bar** — Today · 7d · 30d · 90d · Year · Custom, with automatic previous-period comparison.
- **Executive KPI row** — 4 tiles (Stock Value · Revenue · Transactions · Low Stock) each with a trend sparkline, ▲/▼ delta badge vs the previous equal-length period, and click-to-drill-down.
- **Brand-separated Valuation section** — Brand chips row at the top, then one card per brand containing category-grouped part-type rows with **share-of-brand** progress bars, category subtotals, and a brand subtotal strip. Bottom: gradient emerald Grand Total.
- **Valuation filter bar** — Brand combo + Category combo + "Clear filters" button. Active-filter badge shows how many filters are applied; grand total note shows the active filter context.
- **Sales section** — revenue trend dual-line chart with previous-period ghost overlay, mini-KPIs (sales count · units sold · avg basket · best day), top sellers + top customers HBars with currency formatting.
- **Stock movement section** — IN vs OUT dual-line chart, busiest-hours HBar, colour-coded recent activity feed.
- **Scan invoices section** — 4 KPIs (count · IN total · OUT total · avg), daily IN/OUT dual-line, top-invoice-customers HBar.
- **New UI components** — `KpiTile` (label + sparkline + delta + click), `DeltaBadge` (▲/▼ pill), `SkeletonBlock` (animated shimmer), `EmptyState` upgraded (icon + retry button), `PivotTable` redesigned as brand-separated valuation, `DualLineChart` (current + ghost overlay + hover tooltip).
- **`AnalyticsService` facade** — one class computes every tile's data block, safe to run on worker threads; tiles load independently via `POOL.submit` and swap skeletons for content as each block completes.
- **Drill-down navigation** — click KPI tile, pivot row, or brand chip → navigates to the filtered Inventory / Sales / Transactions page.

### Schema
- **V15 migration** — adds `part_types.default_price` (REAL, nullable) + two new tables `scan_invoices` and `scan_invoice_items` for invoice records, with indexes on date and invoice_id.

### New architecture
- **Repository helpers**: `ItemRepository.get_value_by_brand / get_value_by_part_type / get_value_pivot`; `TransactionRepository.get_daily_aggregates / get_hourly_aggregates`; `SaleRepository.revenue_daily / top_customers`; `InvoiceRepository.get_totals / get_daily / get_top_customers`.
- **`ScanSessionService.commit(layout, customer_name)`** — snapshots each line's price to `scan_invoice_items` so historical invoices stay stable even if prices change later.
- **`PendingScanItem`** — gains `unit_price` (captured at scan time) and a `line_total` property.
- **`HBarChart.set_data(..., value_format=callable)`** — optional formatter so chart values render with the shop currency (`€12,340.00`) instead of bare integers.

### Fixed
- **Discrepancy report crash** — added missing `_GRAY_700` / `_GRAY_100` colour constants and implemented the missing `_safe()` sanitiser. PDFs render without `NameError` / `AttributeError`.
- **Column overflow on inventory + transaction reports** — widths re-balanced so columns sum to exactly 186 mm (usable page width).
- **Missing page numbers / orphaned continuation pages** — fixed by header/footer overrides.
- **Reports now save to `%LOCALAPPDATA%\StockPro\StockManagerPro\reports\`** — same tree used by invoices and backups (was `%TEMP%`).
- **Valuation pivot ambiguous column bug** — renamed the SQL alias to `brand_name` to avoid clashing with `phone_models.brand` / `inventory_items.brand`, then GROUP BY on the full expression.
- **Brand attribution in reports** — every report resolver now falls back through `model_brand → brand → "(no brand)"`; matrix items no longer show as "(no brand)".
- **Analytics valuation scope** — includes zero-stock brand/part-type combos so the full inventory scope is visible (no more "only Apple and Samsung"); grand total unaffected since zeros add nothing.

### Changed
- **Transaction report** accepts a date range + operation filter (was hardcoded to 30 days with no op filter).
- **Backward-compatible analytics refresh API** — `_fetch_all_data` + `_apply_all_data` still exist so `main_window`'s existing `POOL.submit("analytics_refresh", …)` continues to work; the new implementation forwards to `refresh()` on the main thread.

---

## [2.3.8] - 2026-04-17

### Added
- **Content-aware column widths** — every table column now sizes to `max(proportional_target, header_text_fit, widest_cell_fit)` at the active font, so headers and model names are ALWAYS fully visible at any zoom level. Applied to matrix, inventory, transactions, and admin tables.
- **Per-item font scaling** — matrix items with individual `setFont` (`_FONT_MODEL` 11pt, `_FONT_COLOR` 9pt, `_FONT_BRAND` 12pt, `_FONT_DATA` 10pt, `_FONT_MONO` 11pt) now scale correctly via a new `BASE_PT_ROLE` marker that remembers each item's 100% point size
- **Real-time live zoom on slider drag** — every slider tick applies zoom through the 16 ms coalescer; drag feels instant with no lag

### Changed
- **Only the active tab is re-zoomed** on slider changes — previously all 6 matrix tabs were iterated every tick (~15 000 items rebuilt per drag step). Inactive tabs catch up lazily when the user navigates to them via `matrix_tab.refresh()`.
- **QFont cache keyed by (family, weight, base_pt)** — a typical matrix has ~1000 items but only ~5 unique font variants; reusing the cached `QFont` instances drastically reduces allocations during zoom
- **Widget-level QSS on QHeaderView** — overrides app-wide `font-size: 11px` and `padding: 10px 16px` so programmatic `setFont` actually takes effect; header height scales with the font + proportional vertical padding
- **Footer zoom widget fully locked** — every child (slider, buttons, preset, divider) uses `Fixed/Fixed` size policy with `setFixedSize`; preset button is `setFixedSize(56, 22)` so percentage text changes ("50%" ↔ "200%") never shift the layout

### Fixed
- **Table headers disappearing at low zoom** — caused by app-wide QSS overriding per-table `setFont`; now overridden with widget-level stylesheet so headers render at the actual scaled font
- **Model names clipped** — column now measures widest model cell using that cell's own scaled font, not the widget default
- **Footer zoom group stretching during drag** — every inner widget locked to `Fixed` size policy and the group itself pinned to a fixed total width
- **Zoom slider lag** — live-drag now handled via a 16 ms coalescing timer in `ZoomService` plus visible-tab-only dispatch; slider release commits synchronously

---

## [2.3.7] - 2026-04-17

### Added
- **Professional table zoom** — `ZoomService` singleton drives footer-slider zoom for data tables only: matrix tabs (Displays, Batteries, Cases, …), inventory product table, transaction table, and every QTableWidget inside admin panels. Clean separation from app-chrome sizing.
- **Redesigned footer zoom widget** — zoom-out button + slider with tick marks at every preset + zoom-in button + preset dropdown (50/75/100/125/150/200 + Fit + Reset) + reset button; grouped in a bordered pill with proper QToolButton hover/pressed states
- **Zoom persistence** — table zoom saved to `ShopConfig.zoom_level`, restored on launch; 500ms debounced save so slider drags don't hit the DB
- **UI Scale admin setting** — new dropdown in Shop Settings → Regional & Display: Small (85%), Normal (100%), Large (115%), Extra Large (130%). Controls overall app chrome size (sidebar, header, footer, base font). Restart required — shows a dialog confirmation on change.
- **Slimmer sidebar default** — base width reduced from 240 px → 192 px for a more professional look; UI Scale enlarges it if the user prefers

### Changed
- **Zoom scope limited to tables** — sidebar, header, footer, dashboard KPI cards, analytics charts no longer respond to the footer zoom slider (by design — use UI Scale for chrome sizing)
- **Truly proportional table scaling** — removed arbitrary font floors (9pt body / 8pt header); minimum 6pt for genuine shrinking at 50% zoom. Column widths, row heights, padding all scale via `ZOOM.scale(base, minimum)` — no hard floors fighting the zoom
- **Zoom shortcuts centralised** — Ctrl+=, Ctrl++, Ctrl+-, Ctrl+0, Ctrl+Scroll all route through `ZoomService` so footer + shortcuts + wheel stay in sync
- **Matrix refresh preserves zoom** — after refresh, containers re-apply current zoom factor directly (no round-trip through main window)

### Fixed
- **Header truncation at low zoom** — eliminated by proportional column/padding scaling and lower font floor
- **Zoom reset on tab refresh** — matrix tabs now re-apply zoom to all rebuilt brand containers unconditionally

---

## [2.3.6] - 2026-04-16

### Fixed
- **Undo/redo UI freeze** — undo and redo operations now run on the worker pool instead of the main thread, so the window stays fully responsive during the operation
- **Undo/redo real-time refresh** — after an undo/redo, the currently visible tab (inventory, matrix, transactions, analytics) now refreshes in place; you no longer need to switch tabs and come back to see the changes
- **Undo/redo button responsiveness** — undo/redo buttons re-enable immediately after the DB operation completes, before the view refresh; chained undos feel instant
- **Header truncation at low zoom** — header labels (`MIN-VORRAT`, `BESTELLUNG`, `DIFFERENZ`, `BESTAND`) now stay fully visible when zooming out; column widths measured against the new font and padded with a generous 48px buffer

### Changed
- **Thread-safe undo commands** — all undo/redo command lambdas are now DB-only (no UI calls from worker threads); main-thread refresh handled centrally in `_on_undo_done`
- **Inventory filter on undo** — debounce disabled for the post-undo refresh so the product table updates instantly

---

## [2.3.5] - 2026-04-16

### Added
- **Per-brand matrix sections** — "All Brands" view shows separate sections per brand, each with its own correct part-type columns; outer scroll with full-sized sections and sticky headers
- **No Colors option** — "No Colors" button in color picker removes all colour variants for a model, keeping only the base product
- **Expanded colour palette** — added Red, Pink, Yellow, Orange to available colours in settings and matrix picker

### Fixed
- **Brand display cleanup** — Samsung/Xiaomi no longer show Apple-only part types (stale inventory rows cleaned on startup)

---

## [2.4.3] - 2026-04-23

### Added
- **Shop setting: "Show color totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under "Show sell totals"). When off, the per-color sub-rows hide their SELL / COST / TOTAL cells (rendered as `—`, not editable), so valuation is only shown on the model summary row. Useful when all color variants share the same price — the per-color repeats are just noise. Persisted via `ShopConfig.show_color_totals` (reuses `app_config`, no migration). Typed accessor `ShopConfig.is_show_color_totals`. Default ON — existing layouts unchanged until toggled.
- **Color picker on aggregate stock edits** — when a model has color variants, double-clicking STOCK on the model summary row now pops a "Choose Color" dialog (listing the variants of that model × part-type). Previously the edit silently landed on whichever sibling was returned first (usually White), because the parent row's meta held `any_item.id` — a real bug that let stock ops overwrite the wrong color. Uses `ItemRepository.get_colored_siblings`.

### Changed
- **Sell / cost price edits on aggregate rows propagate to all color variants.** Editing SELL or COST on the model summary row of a colored model now writes the new price to every sibling in one pass, with a single bundled undo entry (`Sell <model>·<part> all colors → X` / `Cost … all colors → X`). The prompt title gains a "(all colors)" suffix and a trailing note so it's obvious what's about to happen. Single-color (non-aggregate) edits keep the previous per-item behaviour. Rationale: in practice variants of the same model share pricing — editing one and not the rest was a common source of drift.

### Fixed
- **Aggregate stock edits no longer silently hit the wrong color.** See the color-picker note above.

---

## [2.4.2] - 2026-04-21

### Added
- **Shop setting: "Show sell totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under UI Scale). When off, the matrix TOTAL column and the value portion of the per-part-type cards + the grand-total card are hidden, so shop assistants see stock counts without seeing sell valuation. Units stay visible either way. Cost mode (PIN-gated via 👁) overrides the hide so the cost/sell comparison still makes sense when the owner has authenticated.
  - Persisted via `ShopConfig.show_sell_totals` (reuses the existing `app_config` key-value mechanism — no DB migration needed).
  - Typed accessor `ShopConfig.is_show_sell_totals`.
  - Default is ON — existing users see zero change until they toggle it off.
  - Live-update on Save: the existing settings-close rebuild chain (`ShopConfig.invalidate()` → `rebuild_matrix_tabs()` fast path → `tab.refresh()`) propagates the new state to every matrix tab instantly.

### Fixed
- **Float-precision display bug** — `7 × 22.99` was rendering as `€160.9299999999998` in matrix TOTAL cells and cards. `ShopConfig.format_currency` used `str(amount)` which exposed the full Python-float representation. Now formats with `f"{float(amount):,.2f}"` — always exactly 2 decimals, thousands separator included. One-line fix at source means every money display across the whole app (matrix cells, cards, Quick Scan, Sales, POS, Analytics, Reports, Purchase Orders) benefits automatically.

---

## [2.4.0] - 2026-04-21

### Added
#### Lazy UI construction — startup & settings-close no longer freeze

- **`NavController.register_lazy(key, page_index, factory, on_activate)`** — new API. The factory runs on first navigation; a lightweight `QWidget` placeholder holds the stack slot until then. `register_placeholder(page_index)` + `realize(key)` + `get_lazy_instance(key)` complete the contract.
- **`_MatrixPlaceholder`** — matrix category tabs are now placeholders until the user clicks their sidebar entry. On first click `NavController._go_matrix` swaps the placeholder for a real `MatrixTab` in the same stack slot, emits `navigated`, then kicks the first `refresh()` via `QTimer.singleShot(0, …)` so the switch paints before the DB round-trip lands.
- **10 static pages migrated to lazy**: `SalesPage`, `CustomersPanel`, `PurchaseOrdersPage`, `ReturnsPage`, `BarcodeGenPage`, `ReportsPage`, `SuppliersPage`, `AnalyticsPage`, `AuditPage`, `PriceListsPage`. Each has a closure-style factory that sets `self._xxx_page` before returning; the `AnalyticsPage` factory also wires `navigate_to.connect(nav_ctrl.go)` after construction. Eager pages (`InventoryPage`, `TransactionsPage`, `QuickScanTab`) stay immediate.
- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract for pages/tabs: `self.async_refresh(fetch, apply, key_suffix, debounce_ms)`. Keyed cancellation, `_is_alive()` guard using `sip.isdeleted`, error-path falls through to a non-blocking `_show_empty_state` instead of a modal. Baked into `BaseTab` so every matrix tab inherits it.
- **UI-thread watchdog** (new `app/ui/workers/ui_watchdog.py`) — opt-in via `SM_UI_WATCHDOG=1`. A 10 ms `QTimer` stamps `time.monotonic()`; a daemon thread warns whenever the main thread hasn't heartbeat in > 50 ms. Zero cost when disabled. Regressions that put sync DB calls back on the UI thread show up instantly in the logs.
- **Grand-total card** at the end of the matrix cards strip — emerald-accent anchor showing total units and total valuation across every part-type in the current filter. Metric tag flips `sell` ↔ `cost` with the admin toggle, exactly like the per-part-type cards.

### Performance

- **Worker pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result / error callbacks are gated by the captured epoch so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - `POOL.has_pending(key)` helper so callers can coordinate with in-flight critical workers.
  - `POOL.shutdown(timeout_ms)` — called from `MainWindow.closeEvent`; cancels all work, stops debounce timers, `waitForDone()` the underlying `QThreadPool`. No more leaked workers on exit.
  - Callback error containment: exceptions inside `on_result` / `on_error` are logged instead of silently killing the signal chain.

- **Settings-close freeze — fully resolved.** `ensure_matrix_entries` (can touch 1000+ rows) now runs on `POOL` keyed `"admin:matrix_ensure"`. The admin dialog returns **instantly**. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs` → fast-path, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`). `on_error` fallback still rebuilds so the user never gets a stuck UI on a DB hiccup.

- **`rebuild_matrix_tabs` fast path** — if the active-category set hasn't changed (the common case on settings close), existing realised tabs are KEPT intact and just marked `_dirty=True`; the currently-visible tab gets a refresh via `QTimer.singleShot(0, …)`. Previously rebuild unconditionally nuked every realised tab into a placeholder, leaving the user looking at an empty page for a moment. Only true category adds/removes/reorders take the slow path and recreate placeholders.

- **`MatrixTab.refresh()`** fully async — every DB query (`get_matrix_items`, `get_all`, `get_brands`) runs off the UI thread via `POOL.submit`. In all-brands mode this replaced up to 12 synchronous repo hits per refresh with one pooled fetch; the UI thread no longer touches the DB during brand-combo changes, cost-toggle flips, or post-edit refreshes. `_add_brand_section` / `_reload_brand_container` accept pre-fetched `models=` / `item_map=` kwargs so the worker feeds every brand section at once.

- **Matrix lazy refresh** — per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between tabs. Each tab has a `_dirty` flag; on `COST_VIS.changed`, only the currently visible tab refreshes immediately, others flip `_dirty=True` and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries every time the 👁 button is clicked.

- **`ProductTable.load()`** — replaced per-row `setRowHeight(i, 48)` loop with a single pre-loop `verticalHeader().setDefaultSectionSize(48)`. The per-row call triggered a layout recalc even with `setUpdatesEnabled(False)` — saves 400-600 ms of startup UI-thread work for a 300-item inventory.

- **Per-page async conversions** —
  - `SalesPage._load_products` + `_refresh` split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` combined `po_repo.get_all` + `po_repo.get_summary` into one `POOL.submit_debounced("po_refresh", …, 150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` combined `get_all_audits` + `get_summary` into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **`AnalyticsPage.__init__`** — inline `self.refresh()` deferred via `QTimer.singleShot(0, self.refresh)` so widget-tree construction completes before the skeleton paint + 5 POOL workers fire. Combined with lazy construction, analytics costs nothing until the user actually opens the page.

- **`StartupController._on_ok`** — removed the eager `analytics_page.refresh()` call now that analytics is lazy. Saved 200-400 ms of skeleton-paint + worker dispatch at startup for a page the user may never open.

### Fixed

- **Blank matrix tab after settings close** — root cause was a `POOL.has_pending("admin:matrix_ensure")` guard inside `MatrixTab.refresh()`. Qt dispatches slots in connection order, so user callbacks fire **before** the pool's own `_cleanup` slot; the guard incorrectly returned `True` inside the very callback that was triggered by result delivery. Guard removed (WAL handles concurrent reads safely); the fast-path `refresh()` in `rebuild_matrix_tabs` is now deferred via `QTimer.singleShot(0, …)` so it runs on a clean event-loop idle tick.
- **Silent matrix refresh failures** — `MatrixTab.refresh()`'s `POOL.submit` now has an `on_error` handler that logs the failure with the category key. No more invisible worker exceptions leaving a page blank.
- **`ProductTable.setRowHeight` in loop** — per-row call triggered layout recalcs that `setUpdatesEnabled(False)` couldn't suppress. Moved to `defaultSectionSize` once before the loop.

### Changed

- Matrix staggering experiment reverted — staggering brand sections across ticks via `QTimer.singleShot(0, …)` opened race windows where a second refresh mid-chain left the page blank. Correctness > 200 ms of visual smoothness: `_apply_refresh` builds all sections inline.
- `MainWindow.closeEvent` now calls `POOL.shutdown(2000)` for graceful worker drain.

---

## [2.3.10] - 2026-04-21

### Added
#### Cost valuation — PIN-gated matrix redesign
- **`cost_price` column** on `inventory_items` — purchase / buy price, persisted per item. Schema V16 migration adds the column automatically on first launch.
- **Matrix columns bumped 5 → 7** per part-type group: `MIN-STOCK · DIFFERENCE · STOCK · ORDER · SELL · COST · TOTAL`.
  - **SELL** = the previous "PRICE" column renamed for clarity (item.sell_price with part-type default fallback; edit flow unchanged).
  - **COST** = new, shows `item.cost_price` in the shop's accent blue. **Hidden by default** — only shown after the owner toggles it.
  - **TOTAL** = always visible. Metric flips with the cost toggle:
    - Default: `stock × effective_sell_price`
    - Admin mode: `stock × cost_price`
  - Cell tooltip clarifies which metric is active ("Stock × sell = …" / "Stock × cost = …").
- **👁 cost-visibility toggle** in every matrix tab toolbar. Click prompts for `ShopConfig.admin_pin` (if configured, via `QInputDialog` password-echo — same pattern as `open_admin`). Button swaps closed-eye ↔ talking-eye icon and shows a green accent border when active. One flip fans out to every matrix tab via `CostVisibility.changed`.
- **Professional per-part-type cards** at the top of every matrix tab (name · total units · total valuation · `sell`/`cost` suffix). Live metric — switches from sell-based → cost-based totals when the toggle is on. Card strip lives inside a restored collapsible `BRAND & LEGEND` section alongside the brand filter row.
- **Editable cost_price** — double-click a COST cell (admin mode only) opens the same numeric dialog pattern used for sell; full Undo/Redo via `ItemRepository.update_cost_price()`.
- **Currency symbol everywhere** — SELL, COST, TOTAL cells + tooltips format through a new `_fmt_money()` helper backed by `ShopConfig.format_currency()`.

### New services / repos
- `app/services/cost_visibility.py` — session-local `COST_VIS` singleton (`QObject` with `changed` signal). Default `visible=False` on every app start — nothing persists, so sensitive valuation never leaks on an unattended laptop.
- `ItemRepository.update_cost_price(item_id, new_cost)` — new write method; `_build()` reads `cost_price` when the column exists.
- `_type_visible_width(table, ti)` helper in `matrix_widget.py` — sum of *visible* column widths for a part-type group, so banner chips never over-stretch when the COST column is hidden.
- `_SUB_MIN / _SUB_BB / _SUB_STOCK / _SUB_ORDER / _SUB_SELL / _SUB_PRICE / _SUB_TOTAL` sub-column constants — arithmetic across the matrix now self-documents.

### Performance — professional worker-pool overhaul

- **Pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result and error callbacks are gated by the captured epoch, so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - New `POOL.has_pending(key)` helper so callers can skip a refresh while a critical worker (e.g. `admin:matrix_ensure`) is still writing.
  - New `POOL.shutdown(timeout_ms)` that cancels everything, stops debounce timers, and `waitForDone()` the underlying `QThreadPool`. Called from `MainWindow.closeEvent` — no more leaked workers on exit.
  - Callback-error containment: exceptions inside `on_result` / `on_error` handlers are now logged instead of swallowing the signal stream.

- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract every page/tab now follows:
  - `self.async_refresh(fetch=…, apply=…, key_suffix=…, debounce_ms=…)`
  - Auto-cancels prior task via `POOL` keyed as `f"{POOL_KEY_PREFIX}:{key_suffix}"`.
  - `_is_alive()` guard using `sip.isdeleted` so callbacks skip deleted widgets (tab closed mid-load, language rebuild, etc.).
  - Error path falls through to `_show_empty_state(msg)` inline, not a modal — no more freezing on an error dialog.
  - Baked into `BaseTab` so every matrix tab and future tab gets it for free.

- **Startup freeze — resolved** —
  - `MainWindow._build_ui` defers `rebuild_matrix_tabs()` via `QTimer.singleShot(0, …)`; the main window paints and becomes interactive before any DB work.
  - On first-run setup, `ensure_matrix_entries()` (can touch 1000+ rows) runs on a `POOL` worker; the widget rebuild runs in the `on_result` callback on the main thread.

- **Settings-close freeze — resolved** —
  - Admin-dialog close now submits `ensure_matrix_entries` to `POOL` keyed `"admin:matrix_ensure"`. The dialog returns instantly. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs`, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`).
  - `on_error` fallback still rebuilds tabs so the user never gets a stuck UI on a DB hiccup.
  - `MatrixTab.refresh()` early-returns when `POOL.has_pending("admin:matrix_ensure")` — prevents mid-write reads and sets `_dirty=True` so the tab reconciles on its next `showEvent`.

- **Matrix lazy refresh** —
  - Every `MatrixTab` now has a `_dirty` flag. On `COST_VIS.changed`, only the **currently visible** tab refreshes immediately; others flip the flag and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries when the 👁 button is clicked.
  - Each `MatrixTab` uses a per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between parallel tabs.

- **Per-page migrations off the UI thread** —
  - `SalesPage._load_products` + `SalesPage._refresh` — both split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` — `po_repo.get_all` + `po_repo.get_summary` combined into a single `POOL.submit_debounced("po_refresh", …, delay_ms=150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` — `get_all_audits` + `get_summary` combined into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **UI watchdog** (new `app/ui/workers/ui_watchdog.py`) —
  - Opt-in dev diagnostic enabled via `SM_UI_WATCHDOG=1`.
  - A 10 ms `QTimer` on the UI thread stamps `time.monotonic()`; a daemon thread polls every 50 ms and logs a warning whenever the stamp is older than a configurable threshold (default 50 ms). Instantly surfaces any regression that puts a sync DB call back on the UI thread.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Changed
- Matrix edit dialogs for price split into **Sell Price** and **Cost Price** with distinct titles / Undo labels.
- Cost edit instant-repaints the clicked COST cell + neighbouring TOTAL cell synchronously before the DB refresh lands, so the whole edit lands in a single visual frame. SELL edit does the same for TOTAL when not in cost mode.
- Schema version bumped **15 → 16**.

---

## [2.3.9] - 2026-04-20

### Added
#### Pricing · Quick Scan · Invoices
- **Part-type default price** — Admin → Part Types now has a "Default price" field. Every item inheriting the part type takes that price; per-item `sell_price` still overrides. New "PRICE" column in the part-type admin table.
- **€ / Price column in the matrix** — new column per part type. Green when a per-item override exists, grey when falling back to the part-type default. Double-click to edit; Ctrl+Z undoes.
- **Quick Scan live pricing & totals** — pending table now shows **Unit Price** and **Line Total** per scanned line + a totals card with **ITEMS · SUBTOTAL · GRAND TOTAL** (accent green, JetBrains Mono). Currency formatted via `ShopConfig.format_currency`.
- **Customer field on Quick Scan** — optional input; printed on the invoice when present, otherwise a walk-in record.
- **PDF invoices on every commit** — confirming a scan asks **A4 invoice** or **Thermal receipt**, persists the header + line items, and writes to `%LOCALAPPDATA%\StockPro\StockManagerPro\invoices\INV-YYYYMMDD-NNNN.pdf`. Feed row shows an **Open** button. TAKEOUT → "INVOICE"; INSERT → "STOCK RECEIPT". Layout preference remembered via QSettings.
- **New `ScanInvoiceService`** (A4 + 80 mm thermal fpdf2 layouts) and **`InvoiceRepository`** (day-prefixed numbering + price snapshot per line).

#### Reports — full overhaul
- **5 new reports**: Stock Valuation (per part type, category subtotals, grand total), Sales (with top-10 best sellers), Scan Invoices (IN/OUT history with filter), Expiring Stock (urgency-coloured), Category Performance (stock + movement per category).
- **Inventory report** now groups by **Category → Part Type** with per-section subtotals, a Brand column, and a grand-total emerald bar at the end.
- **Date range picker** on the reports page — presets (Today · 7d · 30d · 90d · This year · Custom) + `QDateEdit` from/to pickers. Applied to every date-aware report.
- **Operation filter** — contextual for Transactions (IN/OUT/ADJUST/CREATE) and Scan Invoices (ALL/IN/OUT).
- **Output path + three actions** — status bar shows the saved PDF path with **Open PDF**, **Open folder** (selects file in Explorer), **Copy path**.
- **`_ReportPDF.header() / footer()` overrides** — shop banner, title subtitle, and `Page X of Y` footer render on **every page** (not just page 1) via `alias_nb_pages()`.
- **Logo support** — `ShopConfig.logo_path` is rendered top-left of every report header when the file exists.
- **Per-table pagination** — every table redraws its column headers on a new page when rows cross the bottom margin.

#### Analytics — professional dashboard
- **Top date-range bar** — Today · 7d · 30d · 90d · Year · Custom, with automatic previous-period comparison.
- **Executive KPI row** — 4 tiles (Stock Value · Revenue · Transactions · Low Stock) each with a trend sparkline, ▲/▼ delta badge vs the previous equal-length period, and click-to-drill-down.
- **Brand-separated Valuation section** — Brand chips row at the top, then one card per brand containing category-grouped part-type rows with **share-of-brand** progress bars, category subtotals, and a brand subtotal strip. Bottom: gradient emerald Grand Total.
- **Valuation filter bar** — Brand combo + Category combo + "Clear filters" button. Active-filter badge shows how many filters are applied; grand total note shows the active filter context.
- **Sales section** — revenue trend dual-line chart with previous-period ghost overlay, mini-KPIs (sales count · units sold · avg basket · best day), top sellers + top customers HBars with currency formatting.
- **Stock movement section** — IN vs OUT dual-line chart, busiest-hours HBar, colour-coded recent activity feed.
- **Scan invoices section** — 4 KPIs (count · IN total · OUT total · avg), daily IN/OUT dual-line, top-invoice-customers HBar.
- **New UI components** — `KpiTile` (label + sparkline + delta + click), `DeltaBadge` (▲/▼ pill), `SkeletonBlock` (animated shimmer), `EmptyState` upgraded (icon + retry button), `PivotTable` redesigned as brand-separated valuation, `DualLineChart` (current + ghost overlay + hover tooltip).
- **`AnalyticsService` facade** — one class computes every tile's data block, safe to run on worker threads; tiles load independently via `POOL.submit` and swap skeletons for content as each block completes.
- **Drill-down navigation** — click KPI tile, pivot row, or brand chip → navigates to the filtered Inventory / Sales / Transactions page.

### Schema
- **V15 migration** — adds `part_types.default_price` (REAL, nullable) + two new tables `scan_invoices` and `scan_invoice_items` for invoice records, with indexes on date and invoice_id.

### New architecture
- **Repository helpers**: `ItemRepository.get_value_by_brand / get_value_by_part_type / get_value_pivot`; `TransactionRepository.get_daily_aggregates / get_hourly_aggregates`; `SaleRepository.revenue_daily / top_customers`; `InvoiceRepository.get_totals / get_daily / get_top_customers`.
- **`ScanSessionService.commit(layout, customer_name)`** — snapshots each line's price to `scan_invoice_items` so historical invoices stay stable even if prices change later.
- **`PendingScanItem`** — gains `unit_price` (captured at scan time) and a `line_total` property.
- **`HBarChart.set_data(..., value_format=callable)`** — optional formatter so chart values render with the shop currency (`€12,340.00`) instead of bare integers.

### Fixed
- **Discrepancy report crash** — added missing `_GRAY_700` / `_GRAY_100` colour constants and implemented the missing `_safe()` sanitiser. PDFs render without `NameError` / `AttributeError`.
- **Column overflow on inventory + transaction reports** — widths re-balanced so columns sum to exactly 186 mm (usable page width).
- **Missing page numbers / orphaned continuation pages** — fixed by header/footer overrides.
- **Reports now save to `%LOCALAPPDATA%\StockPro\StockManagerPro\reports\`** — same tree used by invoices and backups (was `%TEMP%`).
- **Valuation pivot ambiguous column bug** — renamed the SQL alias to `brand_name` to avoid clashing with `phone_models.brand` / `inventory_items.brand`, then GROUP BY on the full expression.
- **Brand attribution in reports** — every report resolver now falls back through `model_brand → brand → "(no brand)"`; matrix items no longer show as "(no brand)".
- **Analytics valuation scope** — includes zero-stock brand/part-type combos so the full inventory scope is visible (no more "only Apple and Samsung"); grand total unaffected since zeros add nothing.

### Changed
- **Transaction report** accepts a date range + operation filter (was hardcoded to 30 days with no op filter).
- **Backward-compatible analytics refresh API** — `_fetch_all_data` + `_apply_all_data` still exist so `main_window`'s existing `POOL.submit("analytics_refresh", …)` continues to work; the new implementation forwards to `refresh()` on the main thread.

---

## [2.3.8] - 2026-04-17

### Added
- **Content-aware column widths** — every table column now sizes to `max(proportional_target, header_text_fit, widest_cell_fit)` at the active font, so headers and model names are ALWAYS fully visible at any zoom level. Applied to matrix, inventory, transactions, and admin tables.
- **Per-item font scaling** — matrix items with individual `setFont` (`_FONT_MODEL` 11pt, `_FONT_COLOR` 9pt, `_FONT_BRAND` 12pt, `_FONT_DATA` 10pt, `_FONT_MONO` 11pt) now scale correctly via a new `BASE_PT_ROLE` marker that remembers each item's 100% point size
- **Real-time live zoom on slider drag** — every slider tick applies zoom through the 16 ms coalescer; drag feels instant with no lag

### Changed
- **Only the active tab is re-zoomed** on slider changes — previously all 6 matrix tabs were iterated every tick (~15 000 items rebuilt per drag step). Inactive tabs catch up lazily when the user navigates to them via `matrix_tab.refresh()`.
- **QFont cache keyed by (family, weight, base_pt)** — a typical matrix has ~1000 items but only ~5 unique font variants; reusing the cached `QFont` instances drastically reduces allocations during zoom
- **Widget-level QSS on QHeaderView** — overrides app-wide `font-size: 11px` and `padding: 10px 16px` so programmatic `setFont` actually takes effect; header height scales with the font + proportional vertical padding
- **Footer zoom widget fully locked** — every child (slider, buttons, preset, divider) uses `Fixed/Fixed` size policy with `setFixedSize`; preset button is `setFixedSize(56, 22)` so percentage text changes ("50%" ↔ "200%") never shift the layout

### Fixed
- **Table headers disappearing at low zoom** — caused by app-wide QSS overriding per-table `setFont`; now overridden with widget-level stylesheet so headers render at the actual scaled font
- **Model names clipped** — column now measures widest model cell using that cell's own scaled font, not the widget default
- **Footer zoom group stretching during drag** — every inner widget locked to `Fixed` size policy and the group itself pinned to a fixed total width
- **Zoom slider lag** — live-drag now handled via a 16 ms coalescing timer in `ZoomService` plus visible-tab-only dispatch; slider release commits synchronously

---

## [2.3.7] - 2026-04-17

### Added
- **Professional table zoom** — `ZoomService` singleton drives footer-slider zoom for data tables only: matrix tabs (Displays, Batteries, Cases, …), inventory product table, transaction table, and every QTableWidget inside admin panels. Clean separation from app-chrome sizing.
- **Redesigned footer zoom widget** — zoom-out button + slider with tick marks at every preset + zoom-in button + preset dropdown (50/75/100/125/150/200 + Fit + Reset) + reset button; grouped in a bordered pill with proper QToolButton hover/pressed states
- **Zoom persistence** — table zoom saved to `ShopConfig.zoom_level`, restored on launch; 500ms debounced save so slider drags don't hit the DB
- **UI Scale admin setting** — new dropdown in Shop Settings → Regional & Display: Small (85%), Normal (100%), Large (115%), Extra Large (130%). Controls overall app chrome size (sidebar, header, footer, base font). Restart required — shows a dialog confirmation on change.
- **Slimmer sidebar default** — base width reduced from 240 px → 192 px for a more professional look; UI Scale enlarges it if the user prefers

### Changed
- **Zoom scope limited to tables** — sidebar, header, footer, dashboard KPI cards, analytics charts no longer respond to the footer zoom slider (by design — use UI Scale for chrome sizing)
- **Truly proportional table scaling** — removed arbitrary font floors (9pt body / 8pt header); minimum 6pt for genuine shrinking at 50% zoom. Column widths, row heights, padding all scale via `ZOOM.scale(base, minimum)` — no hard floors fighting the zoom
- **Zoom shortcuts centralised** — Ctrl+=, Ctrl++, Ctrl+-, Ctrl+0, Ctrl+Scroll all route through `ZoomService` so footer + shortcuts + wheel stay in sync
- **Matrix refresh preserves zoom** — after refresh, containers re-apply current zoom factor directly (no round-trip through main window)

### Fixed
- **Header truncation at low zoom** — eliminated by proportional column/padding scaling and lower font floor
- **Zoom reset on tab refresh** — matrix tabs now re-apply zoom to all rebuilt brand containers unconditionally

---

## [2.3.6] - 2026-04-16

### Fixed
- **Undo/redo UI freeze** — undo and redo operations now run on the worker pool instead of the main thread, so the window stays fully responsive during the operation
- **Undo/redo real-time refresh** — after an undo/redo, the currently visible tab (inventory, matrix, transactions, analytics) now refreshes in place; you no longer need to switch tabs and come back to see the changes
- **Undo/redo button responsiveness** — undo/redo buttons re-enable immediately after the DB operation completes, before the view refresh; chained undos feel instant
- **Header truncation at low zoom** — header labels (`MIN-VORRAT`, `BESTELLUNG`, `DIFFERENZ`, `BESTAND`) now stay fully visible when zooming out; column widths measured against the new font and padded with a generous 48px buffer

### Changed
- **Thread-safe undo commands** — all undo/redo command lambdas are now DB-only (no UI calls from worker threads); main-thread refresh handled centrally in `_on_undo_done`
- **Inventory filter on undo** — debounce disabled for the post-undo refresh so the product table updates instantly

---

## [2.3.5] - 2026-04-16

### Added
- **Per-brand matrix sections** — "All Brands" view shows separate sections per brand, each with its own correct part-type columns; outer scroll with full-sized sections and sticky headers
- **No Colors option** — "No Colors" button in color picker removes all colour variants for a model, keeping only the base product
- **Expanded colour palette** — added Red, Pink, Yellow, Orange to available colours in settings and matrix picker

### Fixed
- **Brand display cleanup** — Samsung/Xiaomi no longer show Apple-only part types (stale inventory rows cleaned on startup)

---

## [2.3.4] - 2026-04-12

### Added
- **Sticky model column** — frozen left-side table for model names stays visible when scrolling horizontally in the matrix
- **Part-type banner bar** — colour-coded part-type names displayed above column headers via synced QScrollArea
- **Excel-like zoom** — Ctrl+Scroll / Ctrl+Plus/Minus zoom (50–200%) with compact footer slider, auto-reset on page switch, hidden on non-table pages
- **Per-model product colours** — right-click any model row in the matrix to select which colours (Black, Silver, Gold…) per model; same toggle UI in settings Admin → Part Types → Model Colors section (double-click to edit)
- **Series separators** — thin visible divider lines between model series groups (X-series, 11-series, A0x, A1x, S2x) for easier reading
- **Collapsible matrix toolbar** — inventory-style clickable section header to hide/show brand filter and legend chips
- **Auto-fit model column** — frozen model column width auto-sizes to the longest model name
- **Live clock** — footer timestamp updates every second automatically
- **Professional splash screen** — geometric inventory cube icon drawn with QPainter, dynamic version badge from `APP_VERSION`, rounded card with emerald glow
- **Custom app icon** — isometric cube icon as `.ico` (multi-resolution 16–256px) and `.png`, used for window, taskbar, installer, and README
- **Full actions toolbar** — New Product, Export CSV, Import CSV, Report, Bulk Edit, Refresh buttons in inventory dashboard
- **Model reorder** — move up/down buttons in Admin → Models panel (same style as part types)
- **Per-model colours in settings** — Admin → Part Types → Model Colors card shows all models with their colour overrides; double-click to edit
- **Import CSV** — toolbar button opens file picker and imports inventory data directly

### Fixed
- **Theme toggle persistence** — toggling theme now saves to database; closing admin no longer reverts to old theme
- **Theme toggle UI** — sidebar, header, footer, matrix legend chips, inventory section headers all update correctly
- **Zoom separators** — separator rows stay at fixed 3px height during zoom
- **Worker pool crash** — wrapped signal emit in try/except to handle widget deletion during background tasks
- **QFont warning** — suppressed harmless `QFont::setPointSize` Qt warning via `qInstallMessageHandler`
- **UAC rejection** — `launch_installer()` returns `bool`; app only quits if UAC was accepted
- **Download cancel** — cancel button on update download progress dialog
- **Installer cache** — downloaded installer stored in persistent `%LOCALAPPDATA%` cache instead of temp dir
- **Cached installer reuse** — if installer already downloaded and SHA256 matches, skip re-download
- **CSV export** — now opens file save dialog instead of crashing on missing `file_path` argument
- **Quick action undo** — +1/-1 buttons now show undo toast (same as full stock dialog)
- **Quick action detail sync** — +1/-1 updates the detail bar instantly (stock count, status badge)
- **Model reorder** — fixed `reorder()` to preserve brand-specific sort_order base; `get_all()` now sorts by `sort_order` instead of re-sorting naturally
- **Per-model colour removal** — unselected colours now properly deleted from ALL part types, not just one

### Changed
- **Schema V14** — 5 new performance indexes on `inventory_items` (active, stock, part_type_id, model+pt, model+pt+color)
- **Connection pooling** — thread-local cached connections instead of new `sqlite3.connect()` per query
- **SQLite optimised** — `synchronous=NORMAL`, `cache_size=20MB`, `temp_store=MEMORY` pragmas
- **Batch inserts** — `_ensure_all_entries()` uses `executemany()` instead of per-row INSERT (10-50x faster)
- **Deferred health checks** — `run_startup_checks()` moved to background thread after 2s delay
- **Lazy theme loading** — only generates QSS for active theme at startup, not all 4
- **Matrix rendering** — pre-indexed item_map for O(1) model lookup; `setUpdatesEnabled(False)` during bulk cell creation
- **Slim dropdown style** — all QComboBox across the app use minimal bottom-line style (transparent, no box border)
- **Compact filter bar** — 26px controls, no container frame, category inline, icon-only reset button
- **Compact actions bar** — 36px toolbar with 6 action buttons, keyboard hints, themed styles
- **Version unified** — `main.py` and splash screen import `APP_VERSION` from `version.py`
- **Pre-release version parsing** — strips `-rc1`, `-beta` suffixes before comparing
- **Manifest validation** — validates URL format, SHA256 hex, version parseability
- **min_version enforcement** — `check_for_update()` respects `min_version` field
- **CI/CD pipeline** — release branch → PR → auto-merge to main with retry
- **CI version stamping** — auto-stamps `version.py`, `file_version_info.txt`, `.iss`, `README.md` badge

---

## [2.3.3] - 2026-04-11

### Fixed
- German button and column header text no longer truncated (removed hard pixel width caps)
- Product name column now stretches to fill available space in inventory list
- Collapsible inventory sections (Overview, Filters, Selected Item) give table more space when hidden

### Changed
- Release workflow now auto-extracts changelog entry and publishes it to GitHub Release

---

## [2.3.2] - 2026-04-11

### Fixed
- Update manifest URL corrected — auto-update banner now works for all users
- GitHub Actions workflow now pushes manifest to `main` branch so the app can find it

---

## [2.3.1] - 2026-04-11

### Fixed
- German text no longer truncated in matrix table column headers (Stamm-Zahl, Best-Bung, Bestand, Bestellung)
- German button labels no longer clipped in the detail bar (Anpassen → was "Anpass", Bearbeiten → was "Bearbei")
- Removed `setMaximumWidth` caps on all action buttons in the product detail bar

### Changed
- Product name column is now left-aligned and always fills available table width
- Column widths applied via `Interactive` mode — a long barcode no longer steals space from the name column
- Inventory page sections (Overview, Filters, Selected Item) are now individually collapsible — hiding a section gives that space to the product table
- Product table list expands to fill all freed space when sections are collapsed

---

## [2.3.0] - 2026-04-06

### Added
- Full business module suite: Suppliers, Purchase Orders, Sales, Returns, Customers
- Price Lists with margin analysis
- Audit Log with full transaction history
- Analytics dashboard with charts and KPIs
- Multi-location inventory support
- Async background engine with worker pool
- Controller architecture for clean separation of concerns
- Web server interface (Flask) for remote access
- Auto-update system with in-app banner and one-click installer download

### Changed
- Complete UI overhaul with PRO_DARK and PRO_LIGHT themes
- Matrix inventory view with per-model stock tracking
- Sidebar navigation with collapsible sections

---

## [2.2.0] - 2026-02-15

### Added
- Barcode scanning and generation
- RTL layout support for Arabic language
- German (DE) full translation

### Fixed
- Database migration stability improvements

---

## [2.1.0] - 2026-01-10

### Added
- Category-based matrix view for phone repair shops
- Theme system with DARK / LIGHT / PRO_DARK / PRO_LIGHT presets
- i18n framework with EN / DE / AR support

---

## [2.0.0] - 2025-12-01

### Added
- Initial public release
- SQLite inventory with full CRUD
- PyInstaller Windows build
