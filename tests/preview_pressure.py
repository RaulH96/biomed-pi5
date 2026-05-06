# tests/preview_pressure.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from ui.theme import get_stylesheet, Colors
from ui.widgets.pressure_widget import PressureWidget
from processing.pressure_monitor import PressureMonitor


class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.dark = False
        self.setWindowTitle("Preview — PressureWidget vertical")
        self.setMinimumSize(480, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.monitor = PressureMonitor()
        self.widget  = PressureWidget(monitor=self.monitor, dark=False, parent=self)
        lay.addWidget(self.widget)
        self._apply_theme()

    def set_dark(self, dark):
        self.dark = dark
        self._apply_theme()

    def _apply_theme(self):
        bg = Colors.DARK_BG if self.dark else Colors.LIGHT_BG
        QApplication.instance().setStyleSheet(get_stylesheet(self.dark))
        self.setStyleSheet(f"PreviewWindow {{ background:{bg}; }}")

    def closeEvent(self, e):
        self.monitor.shutdown()
        super().closeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = PreviewWindow()
    win.show()
    sys.exit(app.exec())
