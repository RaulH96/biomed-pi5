# ui/main_window.py
import yaml
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSizePolicy, QApplication, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter

from ui.theme import Colors, Fonts, get_stylesheet
from ui.widgets.toast_widget   import ToastWidget
from ui.widgets.welcome_dialog import WelcomeDialog
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
        self._bg_color = QColor(Colors.LIGHT_BG)
        self.setWindowTitle("Biomed Pi5 — Monitor")
        self.setMinimumSize(600, 400)

        self._root = QWidget()
        self._root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(self._root)

        main_lay = QVBoxLayout(self._root)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.stack = QStackedWidget()
        main_lay.addWidget(self.stack, stretch=1)

        # Toast — notificacion discreta sobre el tab bar
        self._toast = ToastWidget(self._root)
        self._toast.setFixedWidth(400)

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

        self._patch_toggles()
        self._switch_tab(0)
        self._apply_theme()
        self._position_toast()
        self._init_storage_timers()

    # ── Toast ─────────────────────────────────────────────────
    def toast(self, msg: str, duration_ms: int = 3000, color: str = None):
        color = color or Colors.GREEN_400
        self._toast.show_message(msg, duration_ms, color)

    def _position_toast(self):
        if not hasattr(self, "_toast"):
            return
        tw = self._toast.width()
        th = self._toast.height()
        x  = (self._root.width() - tw) // 2
        y  = self._root.height() - self.tab_bar.height() - th - 8
        self._toast.move(x, y)
        self._toast.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._position_toast()

    # ── Bienvenida ────────────────────────────────────────────
    def _show_welcome(self):
        import json, uuid
        from pathlib import Path
        dlg = WelcomeDialog(dark=self.dark, parent=self)
        dlg.exec()

        if dlg.choice == "continue":
            patient = {}
            p = Path("config/patient.json")
            if p.exists():
                try:
                    patient = json.loads(p.read_text())
                except Exception:
                    pass
            if "uuid" not in patient:
                patient["uuid"] = str(uuid.uuid4())
                p.write_text(json.dumps(patient, indent=2))
            name = patient.get("name", "anonimo")
            pid  = patient.get("uuid", name)
            if self._sm:
                self._sm.start_session(name, patient_uuid=pid)
            self.toast(f"✓ Sesión iniciada · {name}")

        elif dlg.choice == "change":
            self._switch_tab(3)
            self.toast("👤  Actualiza los datos del paciente y presiona Guardar",
                       duration_ms=6000, color=Colors.AMBER_400)

        else:
            if self._sm:
                self._sm.start_session("anonimo")
            self.toast("Sesión anónima iniciada", color=Colors.SLATE_400)

    # ── Storage timers ────────────────────────────────────────
    def _init_storage_timers(self):
        try:
            from storage.session_manager import SessionManager
            self._sm = SessionManager.get()

            # Temperatura — verifica cada 500ms, lógica de intervalo en session_manager
            self._temp_timer = QTimer(self)
            self._temp_timer.timeout.connect(self._save_temp)
            self._temp_timer.start(500)

            # SpO2 — timer NO inicia aqui, arranca al entrar al tab SpO2
            with open("config/settings.yaml") as _f:
                _scfg = yaml.safe_load(_f).get("storage", {})
            self._spo2_interval = _scfg.get("spo2_save_interval_seconds", 90) * 1000
            self._spo2_timer = QTimer(self)
            self._spo2_timer.timeout.connect(self._save_spo2)
            # No llamar .start() aqui

            # Presion — verifica cada 500ms si hay resultado nuevo
            self._last_bp_result = None
            self._bp_timer = QTimer(self)
            self._bp_timer.timeout.connect(self._save_bp)
            self._bp_timer.start(500)

            # Paciente — al presionar guardar
            self.page_patient.btn_save.clicked.connect(self._on_patient_saved)

            print("[Storage] Timers inicializados")
        except Exception as e:
            print(f"[Storage] No disponible: {e}")
            self._sm = None

        self._show_welcome()

    def _save_temp(self):
        if not self._sm or not self._mlx_driver:
            return
        try:
            temp_text  = self.page_temp.lbl_temp.text()
            badge_text = self.page_temp.lbl_badge.text()
            if temp_text == "--.-" or "Sin" in badge_text:
                self._sm.on_temp_reading(0, "")
                return
            temp_c = float(temp_text)
            state_map = {
                "Normal":          "normal",
                "Normal baja":     "normal_baja",
                "Febricula":       "febricula",
                "Fiebre moderada": "fiebre_moderada",
                "Fiebre alta":     "fiebre_alta",
                "Fiebre muy alta": "fiebre_muy_alta",
                "Hipotermia":      "hipotermia",
            }
            state = state_map.get(badge_text, "normal")
            try:
                max_c     = float(self.page_temp.card_max._value_label.text().replace(" °C", ""))
                min_c     = float(self.page_temp.card_min._value_label.text().replace(" °C", ""))
                ambient_c = float(self.page_temp.card_ambient._value_label.text().replace(" °C", ""))
            except Exception:
                max_c = min_c = ambient_c = None
            saved = self._sm.on_temp_reading(
                temp_c, state, max_c=max_c, min_c=min_c, ambient_c=ambient_c
            )
            if saved:
                self.toast(f"🌡 Temperatura guardada · {temp_c}°C · {badge_text}")
        except Exception:
            pass

    def _save_spo2(self):
        if not self._sm or not self._spo2_monitor:
            return
        try:
            if self._sm.on_spo2_stable(self._spo2_monitor):
                spo2 = self._spo2_monitor.spo2
                hr   = self._spo2_monitor.bpm
                self.toast(f"💓 SpO2 guardado · {spo2:.1f}% · {hr} bpm")
        except Exception as e:
            print(f"[Storage] SpO2 error: {e}")

    def _save_bp(self):
        if not self._sm or not self._pressure_monitor:
            return
        try:
            result = self._pressure_monitor.result
            if result and result != self._last_bp_result:
                self._last_bp_result = result
                self._sm.on_bp_result(result)
                sys_v = result["sys"]
                dia_v = result["dia"]
                self.toast(f"🩺 Presión guardada · {sys_v:.0f}/{dia_v:.0f} mmHg")
        except Exception as e:
            print(f"[Storage] BP error: {e}")

    def _on_patient_saved(self):
        if not self._sm:
            return
        try:
            import json
            from pathlib import Path
            name = self.page_patient.f_name._input.text()
            patient_uuid = None
            p = Path("config/patient.json")
            if p.exists():
                data = json.loads(p.read_text())
                patient_uuid = data.get("uuid")
            self._sm.start_session(name, patient_uuid=patient_uuid)
            self.toast(f"✓ Paciente actualizado · {name}")
        except Exception as e:
            print(f"[Storage] Session error: {e}")

    # ── Tema ──────────────────────────────────────────────────
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg_color)
        p.end()

    def _patch_toggles(self):
        win = self
        def make_callback(page):
            def callback(dark: bool):
                page.dark = dark
                page._apply_style()
                win._on_widget_toggle(dark, page)
            return callback
        for page in self._pages:
            if hasattr(page, "switch"):
                page.switch._on_toggle = make_callback(page)

    def _on_widget_toggle(self, dark: bool, source_page):
        self.dark = dark
        self._apply_theme()
        for page in self._pages:
            if page is not source_page and hasattr(page, "set_dark"):
                page.set_dark(dark)

    def _apply_theme(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        tab_bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        self._bg_color = QColor(bg)
        QApplication.instance().setStyleSheet(get_stylesheet(self.dark))
        self.tab_bar.setStyleSheet(
            f"#tab_bar {{ background:{tab_bg}; "
            f"border-top: 0.5px solid {border}; }}"
        )
        self._root.setStyleSheet(f"background: {bg};")
        self.update()

    def set_dark(self, dark: bool):
        self.dark = dark
        self._apply_theme()
        for page in self._pages:
            if hasattr(page, "set_dark"):
                page.set_dark(dark)

    # ── Tabs ──────────────────────────────────────────────────
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

        # Presion — inicializar lazy al entrar al tab
        if active and idx == 2 and self._pressure_monitor is None \
                and _cfg["sensors"]["pressure"].get("enabled", False):
            try:
                from processing.pressure_monitor import PressureMonitor
                self._pressure_monitor = PressureMonitor()
                self.page_pressure.monitor = self._pressure_monitor
                print("[Presion] Monitor inicializado")
            except Exception as e:
                print(f"[Presion] No disponible: {e}")

        # SpO2 timer — solo corre cuando el usuario esta en ese tab
        # Al entrar: inicia desde cero. Al salir: detiene.
        if hasattr(self, "_spo2_timer"):
            if idx == 1 and active:
                self._spo2_timer.start(self._spo2_interval)
            elif idx == 1 and not active:
                self._spo2_timer.stop()
        
        # LEDs SpO2 — apagar al salir, encender al entrar  ← ANTES del return
        if self._spo2_monitor:
            if idx == 1 and active:
                self._spo2_monitor.resume()
            elif idx == 1 and not active:
                self._spo2_monitor.pause()

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

    # ── Sensores ──────────────────────────────────────────────
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

    def closeEvent(self, e):
        if hasattr(self, "_sm") and self._sm:
            self._sm.shutdown()
        if self._pressure_monitor:
            self._pressure_monitor.shutdown()
        if self._spo2_monitor:
            self._spo2_monitor.shutdown()
        super().closeEvent(e)
