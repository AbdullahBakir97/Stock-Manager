"""main.py — Stock Manager Pro entry point"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt
from app.core.logger import get_logger
from app.core.database import DB_PATH
from app.core.version import APP_VERSION

_log = get_logger(__name__)


def _icon_path(name: str) -> str:
    """Resolve icon path whether running from source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "img", name)


def _handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler that logs unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


def _qt_message_handler(msg_type, context, msg):
    """Suppress harmless Qt warnings (QFont pointSize=-1)."""
    if "QFont::setPointSize" in msg:
        return  # suppress — cosmetic Qt quirk with pixel-based CSS fonts
    # Let everything else through to stderr
    sys.stderr.write(f"{msg}\n")


def main():
    # ── Initialize logging ──────────────────────────────────────────────────
    frozen = getattr(sys, "frozen", False)
    _log.info(f"Stock Manager Pro starting (frozen={frozen})")
    _log.info(f"Python version: {sys.version}")
    _log.info(f"Database path: {DB_PATH}")

    sys.excepthook = _handle_exception

    from PyQt6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(_qt_message_handler)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Stock Manager Pro")
    app.setApplicationDisplayName("Stock Manager Pro")
    app.setOrganizationName("StockPro")
    app.setApplicationVersion(APP_VERSION)

    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setWeight(QFont.Weight.Normal)
    app.setFont(font)

    icon = QIcon(_icon_path("icon_cube.ico"))
    app.setWindowIcon(icon)

    # ── Splash screen ────────────────────────────────────────────────────────
    # Show the branded splash immediately so users see activity right away.
    # MainWindow.__init__ calls set_progress() at each build phase.
    from app.ui.components.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()   # force first paint before any heavy work

    # ── Build main window (updates splash as it goes) ────────────────────────
    from app.ui.main_window import MainWindow
    window = MainWindow(splash=splash)
    window.setWindowIcon(icon)

    # ── Hand off to main window ──────────────────────────────────────────────
    window.show()
    splash.finish()   # animates to 100 % then fades out

    # Pre-generate QSS for every theme on idle, so the first toggle is
    # instant instead of paying the ~80ms QSS-string-build cost. Deferred
    # to QTimer.singleShot(0) so it runs on the first event-loop idle
    # tick, after the window has finished its initial paint — no
    # contribution to startup time the user actually sees.
    try:
        from PyQt6.QtCore import QTimer as _QT
        from app.core.theme import THEME as _THEME
        _QT.singleShot(0, _THEME.warm_cache)
    except Exception:
        pass

    # Optional UI-thread watchdog (enable via SM_UI_WATCHDOG=1).
    # Logs a warning when the main thread blocks longer than 50 ms.
    try:
        from app.ui.workers.ui_watchdog import start as _start_watchdog
        _start_watchdog(threshold_ms=50)
    except Exception:
        pass

    _log.info("Main window displayed successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
