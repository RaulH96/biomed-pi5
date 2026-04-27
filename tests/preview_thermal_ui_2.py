import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml
with open("config/settings.yaml") as f:
    cfg = yaml.safe_load(f)
offset = cfg["sensors"]["mlx90640"].get("calibration_offset", 0.0)

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from ui.theme import get_stylesheet, Colors
from ui.widgets.thermal_widget2 import ThermalWidget2
from drivers.mlx90640 import MLX90640Driver

class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.dark = False
        self.setWindowTitle("Preview — ThermalWidget2 horizontal")
        self.setMinimumSize(480, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.thermal = ThermalWidget2(
            driver=MLX90640Driver(), dark=False, offset=offset, parent=self
        )
        lay.addWidget(self.thermal)
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
