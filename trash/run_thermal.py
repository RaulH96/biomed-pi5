import sys
sys.path.insert(0, '/home/harlink/biomed-pi5')

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from ui.theme import get_stylesheet, Colors
from ui.widgets.thermal_widget import ThermalWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dark = False
        self.setWindowTitle("Biomed — Sensor térmico")
        self.setMinimumSize(540, 680)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.root = QWidget()
        self.root.setObjectName("root")
        self.root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(self.root)

        lay = QVBoxLayout(self.root)
        lay.setContentsMargins(20, 20, 20, 20)

        from drivers.mlx90640 import MLX90640Driver
        self.thermal = ThermalWidget(driver=MLX90640Driver(), dark=False, offset=0.7, parent=self)
        lay.addWidget(self.thermal)
        self._apply_theme()

    def set_dark(self, dark: bool):
        self.dark = dark
        self._apply_theme()

    def _apply_theme(self):
        bg = Colors.DARK_BG if self.dark else Colors.LIGHT_BG
        QApplication.instance().setStyleSheet(get_stylesheet(self.dark))
        self.root.setStyleSheet(f"QWidget#root {{ background: {bg}; }}")
        self.setStyleSheet(f"QMainWindow {{ background: {bg}; }}")

app = QApplication(sys.argv)
app.setStyle("Fusion")
win = TestWindow()
win.show()
sys.exit(app.exec())
