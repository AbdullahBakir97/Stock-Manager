"""app/core/version.py — Single source of truth for app version and update URL.

To release a new version:
1. Bump APP_VERSION here.
2. Upload the new installer to the download URL.
3. Update UPDATE_MANIFEST_URL to point to a JSON manifest that contains
   the new version number and installer URL (see UpdateService for schema).
"""
from __future__ import annotations

# ── Current version ────────────────────────────────────────────────────────────
APP_VERSION = "2.0.0"

# ── Update manifest URL ────────────────────────────────────────────────────────
# Host a small JSON file at this URL; UpdateService fetches it periodically.
# Set to "" to disable update checks entirely (e.g. for enterprise air-gapped deployments).
#
# Recommended: use GitHub Releases or any static file host.
# Example manifest format (see UpdateService.fetch_manifest for full schema):
#
#   {
#     "version":      "2.1.0",
#     "download_url": "https://example.com/StockManagerPro-2.1.0-setup.exe",
#     "release_notes":"Bug fixes and new reporting features.",
#     "release_date": "2026-05-01",
#     "checksum_sha256": "abc123..."   (optional – verified before install)
#   }
#
UPDATE_MANIFEST_URL: str = (
    "https://raw.githubusercontent.com/your-org/stock-manager-pro/main/update_manifest.json"
)
