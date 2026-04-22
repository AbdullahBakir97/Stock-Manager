# Stock Manager Pro — Web/Tablet Version
## Phase 2 Engineering Plan

---

## 1. Executive Summary

Stock Manager Pro is today a PyQt6 desktop application with local SQLite
storage, serving a single Windows workstation in a phone-repair shop. **Phase 2
adds a web/tablet companion** that runs as a sidecar process on the same PC
and lets the shop owner and staff operate the store from any tablet or phone
connected to the shop Wi-Fi.

The companion is implemented as a **local FastAPI server + Progressive Web
App**. It shares the desktop app's SQLite database (no sync, no drift), stays
fully offline-capable within the shop, and requires no cloud hosting, no
subscription, no Google Play publishing.

**Delivery:** ~10–14 developer days across 5 phases. Customer sees a branded,
installable-to-home-screen app on their tablet that mirrors desktop
functionality for day-to-day operations.

---

## 2. Goals & Non-Goals

### Goals
- **Operational parity** with the desktop app for the day-to-day workflow
  (inventory, sales, scanning, returns, customer lookup, reports).
- **Installable** on tablet/phone via PWA — home-screen icon, fullscreen,
  feels native.
- **Zero cloud** — everything lives on the shop PC; data never leaves the LAN.
- **Single source of truth** — shared SQLite DB, no synchronization logic.
- **Multilingual** — English / Deutsch / Arabic with RTL, same as desktop.
- **Themed** — matches the desktop's 4 theme system (Dunkel / Hell / Pro
  Dunkel / Pro Hell).
- **Accessibility & performance** — keyboard-friendly, touch-optimized, works
  on a 5-year-old Android tablet over 2.4 GHz Wi-Fi.

### Non-Goals (Phase 2)
- Admin-only operations (migrations, settings, audit log review, PIN reset).
- Bulk CSV import/export — stays on desktop.
- Database backup/restore — desktop-only for safety.
- Cross-site / remote access outside the shop Wi-Fi (deferred to Phase 3
  with Tailscale / Cloudflare Tunnel if requested).
- Native Android/iOS app on the Play Store (explicit strategic decision —
  see §16).

---

## 3. Feature Parity Matrix

| Desktop Module | Tablet/Web Scope | Notes |
|---|---|---|
| **Lagerverwaltung** — browse, search, create, edit | ✅ Full (create/edit gated by PIN role) | Matrix-Ansicht adapted to cards on narrow screens |
| **Stock levels & warnings** (OK/NIEDRIG/KRITISCH/LEER) | ✅ Full | Colored badges, same thresholds |
| **Barcode scan** (USB HID scanner OR camera) | ✅ Full | Camera scan via `BarcodeDetector` API; keyboard-wedge scanner also works |
| **Quick Scan (IN/OUT)** | ✅ Full | 3-step flow identical to desktop |
| **Verkauf** (sales) with customer lookup | ✅ Full | Autocomplete against customer DB |
| **PDF Rechnung** (A4 + thermal) | ✅ Full | Server generates, tablet downloads/prints |
| **Invoice numbering** (INV-YYYYMMDD-NNNN) | ✅ Full | Shared repository, no collisions |
| **Kundendatenbank** — view, create | ✅ Full | Edit/delete gated by role |
| **Lieferanten / Einkauf** | ✅ View + receive | Order entry stays desktop-only in Phase 2 |
| **Retouren / Rückgaben** | ✅ Full | |
| **Mehrere Standorte** (locations) | ✅ Full | Move stock between locations from tablet |
| **Berichte** — Bestandsbewertung, Verkaufsbericht, Transaktionen | ✅ Read-only | PDF export button |
| **Analyse-Dashboard** (KPIs, charts) | ✅ Full | Chart.js / Recharts |
| **Import/Export CSV** | ❌ Desktop only | Safety — batch ops from a trusted context |
| **Backup / Restore** | ❌ Desktop only | |
| **Migrations / Admin** | ❌ Desktop only | |
| **Updates** | ❌ Desktop only | Desktop updater still handles both |
| **Theme switcher** | ✅ 4 themes | Same palette tokens |
| **Language switcher** | ✅ EN / DE / AR (RTL) | Shared i18n catalog |

**Result:** customer gets ~85% of desktop functionality on tablet — everything
operational, nothing administrative.

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Shop Windows PC                             │
│                                                                     │
│   ┌──────────────────┐         ┌──────────────────────────────┐     │
│   │  Desktop app     │         │  FastAPI web server          │     │
│   │  (PyQt6)         │         │  (uvicorn, same process OR   │     │
│   │                  │         │   launched as sidecar)       │     │
│   │  Full feature    │         │                              │     │
│   │  set + admin     │         │  Serves PWA + JSON API       │     │
│   └────────┬─────────┘         └──────────┬───────────────────┘     │
│            │                              │                         │
│            │   app.repositories.*         │                         │
│            │   (shared layer)             │                         │
│            ▼                              ▼                         │
│        ┌────────────────────────────────────────────┐               │
│        │  SQLite DB  —  PRAGMA journal_mode=WAL     │               │
│        └────────────────────────────────────────────┘               │
│                                                                     │
│   mDNS advertises `stockmanager.local` on port 8765                 │
└─────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │  Wi-Fi (LAN)
                                  │
             ┌────────────────────┴────────────────────┐
             │                                         │
     ┌───────▼────────┐                       ┌────────▼───────┐
     │  Tablet        │                       │  Phone         │
     │  (owner)       │                       │  (staff)       │
     │  PWA installed │                       │  PWA installed │
     │  → Full access │                       │  → PIN-limited │
     └────────────────┘                       └────────────────┘
```

### Two processes, one database

The web server is a **separate process** launched by the desktop app on
startup (or as an auto-start service). This gives:
- Independent lifecycles — desktop can restart without killing tablet sessions
- Crash isolation — a web request that crashes the server doesn't kill the UI
- Clear security boundary — the server process runs with least privileges

### Shared code, shared data

Both processes import `app.repositories.*` — the same tested business logic.
The server is a **thin adapter**: HTTP in, repository call, JSON out.

---

## 5. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Web framework** | FastAPI | Async, auto OpenAPI docs, Pydantic validation, mature ecosystem |
| **ASGI server** | Uvicorn | Standard FastAPI companion; fast, stable |
| **Frontend** | Vue 3 + Vite + TypeScript | Shop owner is non-technical but we need a proper SPA; Vue has gentler learning curve than React for the handover. Alternative: HTMX if we want near-zero JS. |
| **Styling** | Tailwind CSS + custom theme tokens | Matches desktop theme values; responsive out of the box |
| **Charts** | Chart.js | Lighter than Recharts, works with Vue via vue-chartjs |
| **Barcode scan (camera)** | Native `BarcodeDetector` API + `@zxing/browser` fallback | Native API fast on Chrome/Android; fallback covers older devices |
| **PWA tooling** | Vite-PWA plugin (Workbox) | Manifest, service worker, precache — one plugin |
| **i18n** | vue-i18n | EN/DE/AR with RTL mirroring |
| **State** | Pinia | Standard Vue 3 state mgmt |
| **mDNS** | python-zeroconf | Pure-Python, works on Windows without extra deps |
| **Auth** | FastAPI + passlib (argon2) + jose (JWT) | Industry standard, no cloud service needed |
| **Rate limiting** | slowapi | Simple in-process limiter, enough for LAN |
| **Tests** | pytest + httpx + playwright | Unit, integration, E2E |

---

## 6. Data Layer — SQLite Concurrency

Two processes writing to one SQLite file needs care. Plan:

1. **WAL mode enabled** at startup by whichever process opens first:
   ```sql
   PRAGMA journal_mode = WAL;
   PRAGMA synchronous  = NORMAL;
   PRAGMA busy_timeout = 5000;   -- 5s retry
   PRAGMA foreign_keys = ON;
   ```
2. **Short transactions only.** No long-running transactions on either side.
3. **Single writer at a time** — SQLite enforces this, we just avoid unnecessary
   write locks (don't wrap reads in `BEGIN IMMEDIATE`).
4. **Connection per request** on server side (don't share connections across
   threads).
5. **Checkpoint policy** — let SQLite auto-checkpoint; backup tool respects
   `-wal` / `-shm` sidecar files.
6. **Migration coordination** — only the desktop app runs migrations; server
   refuses to start if DB schema version doesn't match its expected version.

---

## 7. API Design

### Principles
- **RESTful JSON** — predictable, easy to debug in browser dev tools.
- **Resource URLs** — `/api/v1/items`, `/api/v1/sales`, `/api/v1/customers`.
- **Explicit versioning** — `/api/v1/` prefix so we can ship v2 alongside v1.
- **Uniform error envelope** — `{"error": {"code", "message", "details"}}`.
- **Idempotent writes** — client-supplied request IDs on sales & stock moves
  so double-taps don't double-sell.
- **OpenAPI schema auto-exposed** at `/api/v1/openapi.json` for internal use.

### Endpoint sketch (Phase 2 MVP)

```
POST   /api/v1/auth/pair          # device pairing
POST   /api/v1/auth/login         # PIN -> JWT
POST   /api/v1/auth/refresh

GET    /api/v1/items              # list + search + filter
GET    /api/v1/items/{id}
GET    /api/v1/items/by-barcode/{barcode}
POST   /api/v1/items              # (role: manager+)
PATCH  /api/v1/items/{id}

GET    /api/v1/stock              # stock levels per location
POST   /api/v1/stock/adjust       # Quick Scan IN/OUT
POST   /api/v1/stock/transfer     # location → location

GET    /api/v1/customers
POST   /api/v1/customers

GET    /api/v1/sales
POST   /api/v1/sales              # creates invoice + decrements stock
GET    /api/v1/sales/{id}/invoice.pdf

GET    /api/v1/returns
POST   /api/v1/returns

GET    /api/v1/reports/stock-value
GET    /api/v1/reports/sales
GET    /api/v1/reports/transactions
GET    /api/v1/reports/dashboard  # KPI bundle

GET    /api/v1/meta/version       # schema + app version
GET    /api/v1/meta/health        # liveness
```

---

## 8. Authentication & Authorization

### Device pairing (one-time)
1. On desktop: *Admin → Add device* shows a QR code containing a short-lived
   pairing token (5-minute TTL, single use).
2. On tablet: scan QR in any camera app or browser → opens
   `http://stockmanager.local:8765/pair?t=…`.
3. Server exchanges pairing token for a long-lived **device token** stored
   in IndexedDB on the tablet.
4. Device registered in `devices` table: `{id, name, role, created_at,
   last_seen, revoked_at}`.

### Session login
- Every app launch: PIN → short-lived JWT (1 hour), refreshed silently.
- PIN matches the desktop PIN system (same hash, same lockout policy).
- Biometric unlock via WebAuthn added in Phase 2.5 if requested.

### Roles (minimum)
- **Admin** (owner) — full access except what's desktop-gated.
- **Manager** — stock edits, sales, returns, reports.
- **Cashier** — sales + returns only, view stock, no edits.

Role is stored per-device in the `devices` table so the tablet at the counter
is always "cashier" regardless of who holds it.

### Authorization model
- FastAPI dependency `require_role("manager")` on each endpoint.
- All writes log `{device_id, user_pin_holder?, action, entity, before, after}`
  into the existing audit log.

---

## 9. Frontend Architecture (PWA)

### App shell
- **Single-page Vue 3 app** — loads instantly from cache after first visit.
- **Responsive layout** — portrait (phone), landscape (tablet), kiosk (TV).
- **Left nav drawer** (tablet) or bottom tab bar (phone): Stock · Sell ·
  Scan · Customers · Reports · Settings.

### Key screens
1. **Login** — numeric keypad, big touch targets, error on wrong PIN.
2. **Home dashboard** — KPI tiles mirroring desktop (stock value, today's
   sales, low stock count, transactions today).
3. **Stock list** — searchable, filterable by brand/category/location,
   sortable. Tap → item detail.
4. **Item detail** — photo (if any), pricing, stock per location, recent
   transactions.
5. **Scan mode** — fullscreen camera viewfinder with corner overlay + IN/OUT
   toggle + quantity stepper + "commit" FAB.
6. **Quick Sale** — scan items → review cart → enter customer → confirm →
   PDF invoice shown with print/share.
7. **Customers** — searchable list, tap for purchase history.
8. **Reports** — tabs for each report, date-range picker, export-PDF button.
9. **Settings** — theme, language, device name, logout, sync status.

### PWA manifest highlights
```json
{
  "name": "Stock Manager Pro",
  "short_name": "StockMgr",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1F2A44",
  "background_color": "#0B0F1A",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable.png", "sizes": "512x512",
      "type": "image/png", "purpose": "maskable" }
  ]
}
```

### Service worker strategy
- **App shell** (HTML/JS/CSS): cache-first, version-pinned.
- **API calls**: network-first with 2s timeout → fall back to cached read-only
  data with a "stale data" banner.
- **Images**: cache-first with a 50 MB LRU budget.
- **Invoice PDFs**: never cached (always fresh).

---

## 10. UI / UX Design System

Shared design tokens between desktop and web so the feel is consistent.

### Color tokens (already in desktop themes)
| Token | Dunkel | Hell | Pro Dunkel | Pro Hell |
|---|---|---|---|---|
| `--bg` | #0B0F1A | #FFFFFF | #000814 | #F6F8FA |
| `--surface` | #111827 | #F6F8FA | #0B1220 | #FFFFFF |
| `--text` | #F3F4F6 | #111827 | #E5E7EB | #0F172A |
| `--muted` | #9CA3AF | #6B7280 | #94A3B8 | #64748B |
| `--accent` | #10B981 | #10B981 | #34D399 | #059669 |
| `--border` | #1F2937 | #E5E7EB | #0F172A | #E2E8F0 |
| `--danger` | #EF4444 | #DC2626 | … | … |

### Typography
- System font stack: `-apple-system, "Segoe UI", Roboto, "Noto Sans Arabic",
  sans-serif`.
- Modular scale: 12 / 14 / 16 / 18 / 22 / 28 / 36.
- Line-height 1.4 body, 1.2 display.
- RTL support — fonts swap to Noto Naskh Arabic for Arabic locale.

### Spacing & layout
- 4px grid, Tailwind default.
- Touch targets minimum 44×44 px (WCAG).
- Safe areas respected on tablet (home indicator, notch).

### Motion
- Minimal — 150 ms fades, 200 ms slides. Respect `prefers-reduced-motion`.

---

## 11. Network Discovery & Installation

### mDNS advertising
`python-zeroconf` publishes:
- Service: `_stockmanager._tcp.local.`
- Hostname: `stockmanager.local`
- Port: `8765`

Tablets on the same Wi-Fi resolve `http://stockmanager.local:8765/` without
typing any IP.

### Windows firewall
Desktop installer adds a firewall rule on install:
```
netsh advfirewall firewall add rule \
  name="Stock Manager Web" \
  dir=in action=allow protocol=TCP localport=8765
```

### First-time install on tablet
1. Owner types `stockmanager.local:8765` in Chrome (one time).
2. Chrome offers *Add to Home Screen*.
3. App installs with icon, launches fullscreen next time.

### If mDNS fails (some Wi-Fi routers block it)
Fallback: desktop shows a QR code with the PC's LAN IP
(`http://192.168.1.50:8765/pair?t=…`). Tablet scans, app stores the IP, never
needs it again.

---

## 12. Security

| Concern | Mitigation |
|---|---|
| Tablet stolen | Device token revocable from desktop admin panel; PIN required every launch |
| Someone sniffs LAN | Optional TLS in Phase 2.5 with mkcert-generated cert pushed to devices. Phase 2 ships HTTP since LAN is trusted. |
| Brute-force PIN | Same lockout as desktop: 5 wrong → 5 min cooldown, 10 wrong → device disabled |
| Replay attacks | JWT has 1 h expiry + device-bound `jti` |
| SQL injection | Parameterized queries only (already the standard in `app/repositories`) |
| XSS | Vue auto-escapes; no `v-html` with user input |
| CSRF | Bearer tokens, not cookies — CSRF not applicable |
| Unauthorized scanning | Camera permission only granted per-device by owner |
| Audit gap | Every write logs `device_id` + timestamp in existing audit table |

---

## 13. Offline Support

Tablets lose Wi-Fi when the owner steps into the back room. Design for it.

### Read side
- Last-loaded stock list cached via service worker — viewable offline with
  a "Stale data — last updated 14 min ago" banner.

### Write side
- **Phase 2:** writes require online — UI disables the sell button and shows
  "Offline — reconnect to complete sale".
- **Phase 2.5 (optional):** enqueue writes in IndexedDB, sync on reconnect
  with conflict resolution. Adds complexity; defer unless customer asks.

Reasoning: a phone-repair shop isn't a mobile food truck — the Wi-Fi will be
there. Offline writes are nice-to-have, not must-have.

---

## 14. Project Structure

Proposed layout inside the existing `stock-manager/src/files/`:

```
src/files/
├── app/
│   ├── repositories/           # existing — unchanged
│   ├── services/               # existing — unchanged
│   └── web/                    # NEW
│       ├── __init__.py
│       ├── server.py           # FastAPI app factory
│       ├── launcher.py         # start/stop sidecar
│       ├── routes/
│       │   ├── auth.py
│       │   ├── items.py
│       │   ├── stock.py
│       │   ├── sales.py
│       │   ├── customers.py
│       │   ├── returns.py
│       │   └── reports.py
│       ├── schemas/            # Pydantic models
│       ├── deps.py             # auth + DB dependencies
│       ├── security.py         # JWT + PIN + device tokens
│       ├── mdns.py             # zeroconf advertising
│       └── static/             # built PWA (copied on build)
└── web-ui/                     # NEW — Vue frontend source
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── src/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── router.ts
    │   ├── stores/             # Pinia
    │   ├── api/                # typed API client (generated from OpenAPI)
    │   ├── components/
    │   ├── views/
    │   ├── i18n/               # en.json, de.json, ar.json
    │   └── assets/
    └── public/
        ├── manifest.json
        └── icons/
```

Build step: `cd web-ui && npm run build` → output copied to
`app/web/static/`. Desktop installer bundles both.

---

## 15. Implementation Roadmap

### Phase 2.0 — Foundation (2 days)
- [ ] FastAPI skeleton with health endpoint
- [ ] Shared DB connection helper with WAL guarantee
- [ ] Pytest harness wired up
- [ ] CI check: server starts, health returns 200
- [ ] Launcher: desktop app spawns server as subprocess

### Phase 2.1 — Auth & pairing (1.5 days)
- [ ] JWT issuing + refresh
- [ ] PIN validation reusing desktop logic
- [ ] Device pairing endpoint + QR generation on desktop side
- [ ] Role-based route dependencies

### Phase 2.2 — Core read APIs (2 days)
- [ ] `/items`, `/stock`, `/customers`, `/reports/*` (read-only)
- [ ] OpenAPI auto-generated
- [ ] Typed TS client generated from OpenAPI

### Phase 2.3 — Write APIs (2 days)
- [ ] `/stock/adjust`, `/stock/transfer`
- [ ] `/sales` + invoice PDF generation (reuse existing PDF module)
- [ ] `/returns`
- [ ] Idempotency keys
- [ ] Audit logging

### Phase 2.4 — Frontend (3.5 days)
- [ ] Vue + Vite + Tailwind scaffold
- [ ] Theme tokens + 4 themes wired
- [ ] i18n with EN/DE/AR
- [ ] Login + pairing flow
- [ ] Stock list + item detail
- [ ] Scan screen (camera + HID)
- [ ] Quick Sale flow → PDF invoice
- [ ] Reports (read-only views)
- [ ] Dashboard KPI tiles + charts

### Phase 2.5 — PWA + distribution (1 day)
- [ ] Manifest, icons, maskable icon
- [ ] Service worker with app-shell + network-first API
- [ ] Offline banner
- [ ] Install prompt
- [ ] mDNS advertising
- [ ] Windows firewall rule in installer

### Phase 2.6 — Testing & on-site (1.5 days)
- [ ] E2E tests with Playwright on Android emulator
- [ ] Real-tablet test in the shop (1 half-day on-site)
- [ ] Bug bash + polish pass
- [ ] Handover docs (printed quick-start card)

**Total: ~13.5 dev days** (≈ 2.5–3 calendar weeks with review/polish buffer).

---

## 16. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | SQLite write contention under load | Low | Medium | WAL + busy_timeout + short txns; load test with 5 tablets |
| 2 | mDNS blocked by shop router | Medium | Low | IP fallback with QR code already planned |
| 3 | Shop Wi-Fi flaky → bad UX | Medium | Medium | Offline read cache; clear offline banner |
| 4 | Tablet runs older Chrome, no `BarcodeDetector` | Medium | Low | zxing fallback, USB scanner alternative |
| 5 | Customer expects iOS support | Low | Low | PWA works on iOS Safari (with caveats); call out in spec |
| 6 | PIN brute-force via LAN peer | Low | High | Lockout policy, rate limiting, audit log |
| 7 | Desktop updates break server schema mismatch | Medium | Medium | Server startup check on schema version; desktop installer restarts server |
| 8 | Scope creep (customer wants offline writes, iOS features) | High | Medium | Documented non-goals; charge for Phase 3 |
| 9 | Printing from tablet (thermal / network printer) | Medium | Low | PDF download-and-print covers 90%; dedicated thermal BLE printer support deferred |
| 10 | Language font fallback on Android (Arabic) | Low | Low | Self-host Noto Naskh Arabic |

---

## 17. Success Criteria

The Phase 2 release is complete when:

1. Owner installs the PWA on their tablet in under 2 minutes, unaided, using
   the printed quick-start card.
2. Scanning a barcode on the tablet shows stock level in under 1 second on
   shop Wi-Fi.
3. Completing a sale on the tablet (scan → customer → confirm → PDF) takes
   under 30 seconds.
4. Desktop and tablet show identical stock numbers within 2 seconds of any
   change on either side.
5. Losing Wi-Fi for 30 seconds doesn't crash the tablet; reconnect is
   transparent.
6. All three languages (EN/DE/AR) render correctly, RTL for Arabic.
7. All 4 themes render correctly on tablet.
8. 0 critical / P1 bugs open; P2 bugs documented and triaged.
9. 80% backend test coverage on new `app/web/` code.
10. Customer sign-off after 1-week in-shop pilot.

---

## 18. Deliverables Checklist

- [ ] FastAPI server in `app/web/`
- [ ] Vue PWA in `web-ui/`, built and embedded in installer
- [ ] Windows installer updated: firewall rule, auto-start server, icon in system tray
- [ ] Printed quick-start card (DE, A6) — "How to install on your tablet"
- [ ] Admin guide section: *Tablets verwalten* (add/revoke devices)
- [ ] API reference (auto-generated OpenAPI at `/api/v1/docs`)
- [ ] Tests: pytest backend, Playwright E2E
- [ ] Release notes v2.5.0
- [ ] Customer training session (1 hour on-site)

---

## 19. Future Phases (not in Phase 2)

- **Phase 2.5** — TLS with mkcert, offline writes with IndexedDB queue,
  biometric unlock via WebAuthn.
- **Phase 3** — Remote access (Tailscale or Cloudflare Tunnel) for the owner
  to check stock from home.
- **Phase 4** — Multi-shop edition: sync layer so a chain of shops shares a
  central catalog. Requires a proper server architecture shift — scope it
  separately.
- **Phase 5** — Customer-facing kiosk mode: catalog + self-checkout tablet
  at the counter.

---
