"""app/core/version.py — Single source of truth for app version and update URL.

To release a new version:
1. Bump APP_VERSION here.
2. Build installer: installer\build_installer.bat
3. Upload installer to GitHub Releases.
4. Update update_manifest.json with new version, URL, and SHA256.
5. Push update_manifest.json to the repo (UpdateService fetches it on startup).
"""
from __future__ import annotations

# ── Current version ────────────────────────────────────────────────────────────
APP_VERSION = "2.3.9"

# ── Update manifest URL ────────────────────────────────────────────────────────
# UpdateService fetches this JSON on startup to check for new versions.
# Set to "" to disable update checks (e.g. air-gapped enterprise deployments).
UPDATE_MANIFEST_URL: str = (
    "https://raw.githubusercontent.com/AbdullahBakir97/Stock-Manager/main/stock-manager/update_manifest.json"
)
