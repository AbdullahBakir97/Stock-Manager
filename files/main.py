"""main.py — Stock Manager Pro entry point"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt
from app.ui.main_window import MainWindow


def _icon_path(name: str) -> str:
    """Resolve icon path whether running from source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "img", name)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Stock Manager Pro")
    app.setApplicationDisplayName("Stock Manager Pro")
    app.setOrganizationName("StockPro")
    app.setApplicationVersion("1.0.0")

    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    icon = QIcon(_icon_path("icon_logo.ico"))
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
