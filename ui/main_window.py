# ui/main_window.py
import yaml
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSizePolicy, QApplication, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPainter

from ui.theme import Colors, Fonts, get_stylesheet
from ui.widgets.thermal_widget2  import ThermalWidget2
from ui.widgets.spo2_widget2     import SpO2Widget2
from ui.widgets.pressure_widget2 import PressureWidget2
from ui.widgets.patient_widget   import PatientWidget

with open("config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)
with open("config/settings.yaml") as f:
    _offset = yaml.safe_load(f)["sensors"]["mlx90640"].get("calibration_offset", 0.7)


class TabButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self._icon  = icon
        self._label = label
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = self.isChecked()
        p.fillRect(self.rect(), QColor(Colors.TEAL_500 if active else "transparent"))
        p.setPen(QColor("#FFFFFF" if active else Colors.SLATE_400))
        f_icon = QFont("Inter"); f_icon.setPixelSize(20)
        p.setFont(f_icon)
        p.drawText(0, 0, self.width(), 34,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   self._icon)
        f_lbl = QFont("Inter"); f_lbl.setPixelSize(10)
        p.setFont(f_lbl)
        p.drawText(0, 34, self.width(), 22,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   self._label)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dark = False
        self._bg_color = QColor(Colors.LIGHT_BG)   # para paintEvent
        self.setWindowTitle("Biomed Pi5 — Monitor")
        self.setMinimumSize(600, 400)

        # Widget central unico — sin nombre, sin stylesheet propio
        # El fondo lo pinta MainWindow.paintEvent directamente
        self._root = QWidget()
        self._root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(self._root)

        main_lay = QVBoxLayout(self._root)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.stack = QStackedWidget()
        main_lay.addWidget(self.stack, stretch=1)

        self.tab_bar = QWidget()
        self.tab_bar.setObjectName("tab_bar")
        self.tab_bar.setFixedHeight(60)
        tab_lay = QHBoxLayout(self.tab_bar)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.setSpacing(0)
        main_lay.addWidget(self.tab_bar)

        self._init_sensors()

        self.page_temp     = ThermalWidget2(
            driver=self._mlx_driver, dark=False, offset=_offset)
        self.page_spo2     = SpO2Widget2(
            monitor=self._spo2_monitor, dark=False)
        self.page_pressure = PressureWidget2(
            monitor=self._pressure_monitor, dark=False)
        self.page_patient  = PatientWidget(dark=False)

        self._pages = [
            self.page_temp,
            self.page_spo2,
            self.page_pressure,
            self.page_patient,
        ]

        for page in self._pages:
            self.stack.addWidget(page)

        tabs = [
            ("🌡", "Temperatura"),
            ("💓", "SpO2"),
            ("🩺", "Presion"),
            ("👤", "Paciente"),
        ]
        self._tab_btns = []
        for i, (icon, label) in enumerate(tabs):
            btn = TabButton(icon, label)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            tab_lay.addWidget(btn)
            self._tab_btns.append(btn)

        # Patch ANTES de mostrar la ventana
        self._patch_toggles()
        self._switch_tab(0)
        self._apply_theme()

    # ── Fondo propio del QMainWindow ──────────────────────────
    # PyQt6 no pinta el fondo del QMainWindow con stylesheet
    # de forma confiable — lo hacemos con paintEvent directo
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg_color)
        p.end()

    # ── Patch del ToggleSwitch ────────────────────────────────
    def _patch_toggles(self):
        """
        ToggleSwitch guarda el callback en self._on_toggle (privado).
        Reemplazamos ese atributo directamente en cada instancia
        para que apunte a MainWindow en lugar de al widget padre.
        """
        win = self

        def make_callback(page):
            def callback(dark: bool):
                # 1. Actualizar el widget que origino el evento
                page.dark = dark
                page._apply_style()
                # 2. Propagar a MainWindow y al resto
                win._on_widget_toggle(dark, page)
            return callback

        for page in self._pages:
            if hasattr(page, "switch"):
                # _on_toggle es el atributo exacto que ToggleSwitch llama
                page.switch._on_toggle = make_callback(page)

    def _on_widget_toggle(self, dark: bool, source_page):
        self.dark = dark
        self._apply_theme()
        for page in self._pages:
            if page is not source_page and hasattr(page, "set_dark"):
                page.set_dark(dark)

    # ── Tema ──────────────────────────────────────────────────
    def _apply_theme(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        tab_bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE

        # Guardar color para paintEvent
        self._bg_color = QColor(bg)

        # Stylesheet global
        QApplication.instance().setStyleSheet(get_stylesheet(self.dark))

        # tab_bar con stylesheet propio
        self.tab_bar.setStyleSheet(
            f"#tab_bar {{ background:{tab_bg}; "
            f"border-top: 0.5px solid {border}; }}"
        )

        # root solo necesita el color de fondo
        self._root.setStyleSheet(f"background: {bg};")

        # Forzar repintado del fondo propio
        self.update()

    def set_dark(self, dark: bool):
        self.dark = dark
        self._apply_theme()
        for page in self._pages:
            if hasattr(page, "set_dark"):
                page.set_dark(dark)

    # ── Tabs / timers ─────────────────────────────────────────
    def _switch_tab(self, idx: int):
        prev = self.stack.currentIndex()
        self._set_tab_active(prev, False)
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._tab_btns):
            btn.setChecked(i == idx)
            btn.update()
        self._set_tab_active(idx, True)

    def _set_tab_active(self, idx: int, active: bool):
        page = self._pages[idx]
        if not hasattr(page, "timer"):
            return
        if active:
            if not page.timer.isActive():
                page.timer.start()
        else:
            if isinstance(page, PressureWidget2):
                monitor = getattr(page, "monitor", None)
                if monitor and monitor.phase not in ("idle", "done", "error"):
                    return
            page.timer.stop()

    # ── Init sensores ─────────────────────────────────────────
    def _init_sensors(self):
        self._mlx_driver = None
        if _cfg["sensors"]["mlx90640"].get("enabled", False):
            try:
                from drivers.mlx90640 import MLX90640Driver
                self._mlx_driver = MLX90640Driver()
            except Exception as e:
                print(f"[MLX90640] No disponible: {e}")

        self._spo2_monitor = None
        if _cfg["sensors"]["max30102"].get("enabled", False):
            try:
                from processing.spo2_hr import SpO2Monitor
                self._spo2_monitor = SpO2Monitor()
            except Exception as e:
                print(f"[MAX30102] No disponible: {e}")

        self._pressure_monitor = None
        if _cfg["sensors"]["pressure"].get("enabled", False):
            try:
                from processing.pressure_monitor import PressureMonitor
                self._pressure_monitor = PressureMonitor()
            except Exception as e:
                print(f"[Presion] No disponible: {e}")

    def closeEvent(self, e):
        if self._pressure_monitor:
            self._pressure_monitor.shutdown()
        if self._spo2_monitor:
            self._spo2_monitor.shutdown()
        super().closeEvent(e)