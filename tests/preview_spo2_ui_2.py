import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml
with open("config/settings.yaml") as f:
    cfg = yaml.safe_load(f)

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from ui.theme import get_stylesheet, Colors
from ui.widgets.spo2_widget2 import SpO2Widget2
from processing.spo2_hr import SpO2Monitor

class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.dark = False
        self.setWindowTitle("Preview — SpO2Widget2 horizontal")
        self.setMinimumSize(480, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.widget = SpO2Widget2(monitor=SpO2Monitor(), dark=False, parent=self)
        lay.addWidget(self.widget)
        self._apply_theme()

    def set_dark(self, dark):
        self.dark = dark
        self._apply_theme()

    def _apply_theme(self):
        bg = Colors.DARK_BG if self.dark else Colors.LIGHT_BG
        QApplication.instance().setStyleSheet(get_stylesheet(self.dark))
        self.setStyleSheet(f"PreviewWindow {{ background:{bg}; }}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = PreviewWindow()
    win.show()
    sys.exit(app.exec())
