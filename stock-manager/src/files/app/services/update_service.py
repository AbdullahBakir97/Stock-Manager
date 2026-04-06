"""
app/services/update_service.py — Auto-update support for Stock Manager Pro.

Responsibilities:
  - Fetch a remote JSON update manifest (no extra dependencies — stdlib only).
  - Compare the manifest version against the running APP_VERSION.
  - Download the installer to a temp directory with progress callbacks.
  - Verify the download against an optional SHA-256 checksum.
  - Launch the installer and signal the app to quit.

Network calls are intentionally synchronous so callers can run them on a
background QThread without any asyncio complexity.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from app.core.version import APP_VERSION, UPDATE_MANIFEST_URL

log = logging.getLogger(__name__)

# ── Manifest schema ────────────────────────────────────────────────────────────

@dataclass
class UpdateManifest:
    """Parsed update manifest returned by the remote server."""
    version: str               # "2.1.0"
    download_url: str          # direct link to installer .exe
    release_notes: str = ""    # short human-readable changelog
    release_date: str = ""     # "YYYY-MM-DD"
    checksum_sha256: str = ""  # hex digest; empty = skip verification
    min_version: str = ""      # ignore update if running version < min_version


# ── Version helpers ────────────────────────────────────────────────────────────

def _parse_version(v: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z' into (X, Y, Z) — handles 1-3 component versions."""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


def is_newer(remote: str, current: str = APP_VERSION) -> bool:
    """Return True if `remote` is strictly newer than `current`."""
    return _parse_version(remote) > _parse_version(current)


# ── UpdateService ──────────────────────────────────────────────────────────────

class UpdateService:
    """Handles all update-related I/O.  No Qt dependencies — pure Python."""

    _TIMEOUT_S = 10          # network timeout in seconds
    _CHUNK_SIZE = 65_536     # download chunk size (64 KiB)

    def __init__(self, manifest_url: str = "") -> None:
        self._url = manifest_url or UPDATE_MANIFEST_URL

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """False when no manifest URL is configured (e.g. air-gapped deployments)."""
        return bool(self._url.strip())

    def fetch_manifest(self) -> Optional[UpdateManifest]:
        """
        Download and parse the JSON update manifest.

        Returns None if the URL is unconfigured, the server is unreachable,
        or the JSON is malformed — callers treat None as "no update available".

        Raises:
            urllib.error.URLError  — network errors (let callers decide whether to log/retry)
            json.JSONDecodeError   — malformed manifest
        """
        if not self.is_enabled():
            return None

        req = urllib.request.Request(
            self._url,
            headers={"User-Agent": f"StockManagerPro/{APP_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=self._TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        version = data.get("version", "")
        download_url = data.get("download_url", "")
        if not version or not download_url:
            log.warning("UpdateService: manifest missing 'version' or 'download_url'")
            return None

        return UpdateManifest(
            version=version,
            download_url=download_url,
            release_notes=data.get("release_notes", ""),
            release_date=data.get("release_date", ""),
            checksum_sha256=data.get("checksum_sha256", ""),
            min_version=data.get("min_version", ""),
        )

    def check_for_update(self) -> Optional[UpdateManifest]:
        """
        Fetch the manifest and return it only if a newer version is available.

        Returns None when:
          - Update checks are disabled (no manifest URL).
          - Server is unreachable (logged at DEBUG, not raised).
          - Running version is already up-to-date.
        """
        if not self.is_enabled():
            return None
        try:
            manifest = self.fetch_manifest()
        except Exception as exc:
            log.debug("UpdateService: check failed (%s)", exc)
            return None

        if manifest is None:
            return None

        if not is_newer(manifest.version):
            log.debug("UpdateService: up to date (%s)", APP_VERSION)
            return None

        log.info("UpdateService: new version available: %s → %s", APP_VERSION, manifest.version)
        return manifest

    def download(
        self,
        manifest: UpdateManifest,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> str:
        """
        Download the installer to a temp file.

        Args:
            manifest:    The manifest returned by check_for_update().
            progress_cb: Optional callable(bytes_downloaded, total_bytes).
                         Called repeatedly during download for progress UI.

        Returns:
            Absolute path to the downloaded installer file.

        Raises:
            IOError:     If the download fails or checksum verification fails.
        """
        # Determine file extension from URL (default .exe for Windows)
        url = manifest.download_url
        ext = os.path.splitext(url.split("?")[0])[1] or ".exe"
        dest_fd, dest_path = tempfile.mkstemp(
            prefix=f"StockManagerPro_{manifest.version}_",
            suffix=ext,
        )
        os.close(dest_fd)

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"StockManagerPro/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                hasher = hashlib.sha256()

                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(self._CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            progress_cb(downloaded, total)

        except Exception as exc:
            # Clean up partial file
            try:
                os.remove(dest_path)
            except OSError:
                pass
            raise IOError(f"Download failed: {exc}") from exc

        # Verify checksum if provided
        if manifest.checksum_sha256:
            actual = hasher.hexdigest().lower()
            expected = manifest.checksum_sha256.lower()
            if actual != expected:
                os.remove(dest_path)
                raise IOError(
                    f"Checksum mismatch — expected {expected[:12]}…, got {actual[:12]}…"
                )
            log.info("UpdateService: checksum OK (%s)", actual[:16])

        log.info("UpdateService: installer downloaded → %s", dest_path)
        return dest_path

    def launch_installer(self, installer_path: str) -> None:
        """
        Launch the installer and prepare the app to quit.

        On Windows: uses ShellExecute (so UAC prompts correctly).
        On other platforms: falls back to subprocess.Popen.
        Caller is responsible for calling QApplication.quit() afterward.
        """
        if not os.path.isfile(installer_path):
            raise FileNotFoundError(f"Installer not found: {installer_path}")

        if sys.platform == "win32":
            import ctypes
            # ShellExecute with "runas" prompts UAC properly
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", installer_path, None, None, 1
            )
            if result <= 32:
                raise OSError(f"ShellExecute failed with code {result}")
        else:
            # macOS / Linux fallback
            subprocess.Popen([installer_path])

        log.info("UpdateService: installer launched (%s)", installer_path)


# ── Last-checked timestamp helpers ────────────────────────────────────────────

_APP_CONFIG_KEY_LAST_CHECKED = "update_last_checked"


def record_last_checked() -> None:
    """Persist the current UTC timestamp to app_config after a check runs."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        from app.core.database import get_connection
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                (_APP_CONFIG_KEY_LAST_CHECKED, ts),
            )
    except Exception as exc:
        log.debug("record_last_checked: %s", exc)


def get_last_checked() -> str | None:
    """Return the last-checked UTC timestamp string, or None if never checked."""
    try:
        from app.core.database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key = ?",
                (_APP_CONFIG_KEY_LAST_CHECKED,),
            ).fetchone()
            return row["value"] if row else None
    except Exception:
        return None
