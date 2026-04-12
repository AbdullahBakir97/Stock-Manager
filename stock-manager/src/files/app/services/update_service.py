"""
app/services/update_service.py — Auto-update support for Stock Manager Pro.

Responsibilities:
  - Fetch a remote JSON update manifest (no extra dependencies — stdlib only).
  - Compare the manifest version against the running APP_VERSION.
  - Download the installer to a persistent cache directory with progress callbacks.
  - Verify the download against a SHA-256 checksum.
  - Launch the installer with UAC detection and signal the app to quit.

Network calls are intentionally synchronous so callers can run them on a
background QThread without any asyncio complexity.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
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
    """Parse 'X.Y.Z' into (X, Y, Z).

    Handles pre-release suffixes like '2.3.2-rc1' or '2.3.2-beta'
    by stripping everything after a hyphen before parsing.
    """
    try:
        # Strip pre-release suffix: "2.3.2-rc1" → "2.3.2"
        clean = re.split(r"[-+]", v.strip())[0]
        return tuple(int(x) for x in clean.split("."))
    except (ValueError, AttributeError):
        return (0,)


def is_newer(remote: str, current: str = APP_VERSION) -> bool:
    """Return True if `remote` is strictly newer than `current`."""
    return _parse_version(remote) > _parse_version(current)


# ── Cache directory for downloaded installers ─────────────────────────────────

def _cache_dir() -> str:
    """Return a persistent cache directory for downloaded installers.

    Uses %LOCALAPPDATA%/StockPro/StockManagerPro/updates/ on Windows,
    falls back to a temp directory on other platforms. The directory is
    created if it doesn't exist.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
        d = os.path.join(base, "StockPro", "StockManagerPro", "updates")
    else:
        d = os.path.join(tempfile.gettempdir(), "StockManagerPro_updates")
    os.makedirs(d, exist_ok=True)
    return d


# ── Manifest validation ───────────────────────────────────────────────────────

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_URL_RE = re.compile(r"^https?://")


def _validate_manifest(data: dict) -> str | None:
    """Return an error message if the manifest is malformed, or None if valid."""
    version = data.get("version", "")
    url = data.get("download_url", "")

    if not version:
        return "manifest missing 'version'"
    if not url:
        return "manifest missing 'download_url'"
    if not _URL_RE.match(url):
        return f"download_url is not a valid HTTP(S) URL: {url[:60]}"

    sha = data.get("checksum_sha256", "")
    if sha and not _SHA256_RE.match(sha):
        return f"checksum_sha256 is not valid hex (64 chars): {sha[:20]}..."

    # Version must be parseable
    parsed = _parse_version(version)
    if parsed == (0,):
        return f"version is not parseable: {version}"

    return None


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

        # Validate manifest schema
        error = _validate_manifest(data)
        if error:
            log.warning("UpdateService: %s", error)
            return None

        return UpdateManifest(
            version=data["version"],
            download_url=data["download_url"],
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
          - min_version requirement not met (current version too old for direct upgrade).
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

        # Check min_version constraint (if specified)
        if manifest.min_version:
            current = _parse_version(APP_VERSION)
            min_req = _parse_version(manifest.min_version)
            if current < min_req:
                log.warning(
                    "UpdateService: current %s < min_version %s — cannot upgrade directly",
                    APP_VERSION, manifest.min_version,
                )
                return None

        log.info("UpdateService: new version available: %s -> %s", APP_VERSION, manifest.version)
        return manifest

    def download(
        self,
        manifest: UpdateManifest,
        progress_cb: Callable[[int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> str:
        """
        Download the installer to a persistent cache directory.

        Args:
            manifest:     The manifest returned by check_for_update().
            progress_cb:  Optional callable(bytes_downloaded, total_bytes).
            cancel_check: Optional callable() -> bool. If it returns True,
                          download is aborted and IOError is raised.

        Returns:
            Absolute path to the downloaded installer file.

        Raises:
            IOError:     If the download fails, is cancelled, or checksum fails.
        """
        url = manifest.download_url
        ext = os.path.splitext(url.split("?")[0])[1] or ".exe"
        dest_path = os.path.join(
            _cache_dir(),
            f"StockManagerPro-{manifest.version}-setup{ext}",
        )

        # If already downloaded and checksum matches, skip re-download
        if os.path.isfile(dest_path) and manifest.checksum_sha256:
            existing_hash = hashlib.sha256(open(dest_path, "rb").read()).hexdigest()
            if existing_hash.lower() == manifest.checksum_sha256.lower():
                log.info("UpdateService: installer already cached -> %s", dest_path)
                return dest_path

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
                        # Check cancellation
                        if cancel_check and cancel_check():
                            raise IOError("Download cancelled by user")

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
                try:
                    os.remove(dest_path)
                except OSError:
                    pass
                raise IOError(
                    f"Checksum mismatch — expected {expected[:12]}…, got {actual[:12]}…"
                )
            log.info("UpdateService: checksum OK (%s)", actual[:16])

        log.info("UpdateService: installer downloaded -> %s", dest_path)
        return dest_path

    def launch_installer(self, installer_path: str) -> bool:
        """
        Launch the installer and return True if it started successfully.

        On Windows: uses ShellExecute with "runas" (triggers UAC prompt).
        Returns False if the user rejected UAC or the launch failed.
        Caller is responsible for calling QApplication.quit() afterward
        only if this returns True.
        """
        if not os.path.isfile(installer_path):
            raise FileNotFoundError(f"Installer not found: {installer_path}")

        if sys.platform == "win32":
            import ctypes
            # ShellExecuteW returns > 32 on success
            # Returns SE_ERR_ACCESSDENIED (5) if UAC was rejected
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", installer_path, None, None, 1
            )
            if result <= 32:
                if result == 5:  # SE_ERR_ACCESSDENIED — UAC rejected
                    log.info("UpdateService: UAC rejected by user")
                    return False
                log.error("UpdateService: ShellExecute failed with code %d", result)
                return False
        else:
            # macOS / Linux fallback
            subprocess.Popen([installer_path])

        log.info("UpdateService: installer launched (%s)", installer_path)
        return True


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
