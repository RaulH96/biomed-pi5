# ui/widgets/pressure_widget2.py — layout horizontal
import numpy as np
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.theme import Colors, Fonts
from ui.widgets.thermal_widget import ToggleSwitch, _make_shadow
from ui.widgets.pressure_widget import (
    PressureWaveWidget, OscWaveWidget, EnvelopeDialog,
    MeasureButton, PHASE_LABELS,
)
from processing.pressure import filtro_banda

_MIN_OSC_SAMPLES = 64


class PressureWidget2(QWidget):
    """
    Layout horizontal:
    ┌────────────┬────────────────────────────┐
    │  SYS card  │                            │
    │            │   Grafica en vivo          │
    │  DIA card  │                            │
    ├────────────┴────────────────────────────┤
    │  Oscilaciones en vivo                   │
    ├─────────────────────────────────────────┤
    │  MAP │ FC │ Estado │ [Medir][Des][Anal] │
    └─────────────────────────────────────────┘
    """
    def __init__(self, monitor=None, dark=False, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.dark    = dark
        self._last_result    = None
        self._shadow_widgets = []
        self._live_fs        = 100.0
        self._build_ui()
        self._apply_style()
        self._setup_timer()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Encabezado ───────────────────────────────────────
        top = QHBoxLayout()
        col = QVBoxLayout(); col.setSpacing(1)
        lbl_sub = QLabel("Presion arterial · MPX5050 + ADS1115")
        lbl_sub.setFont(Fonts.get(10))
        lbl_sub.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row = QHBoxLayout(); title_row.setSpacing(8)
        lbl_title = QLabel("Tension arterial")
        lbl_title.setFont(Fonts.get(16, QFont.Weight.Medium))
        self.status_dot = QLabel("●")
        self.status_dot.setFont(Fonts.get(9))
        self.status_dot.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row.addWidget(lbl_title); title_row.addWidget(self.status_dot)
        title_row.addStretch()
        col.addWidget(lbl_sub); col.addLayout(title_row)

        sw_col = QVBoxLayout()
        sw_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        lbl_sw = QLabel("Oscuro"); lbl_sw.setFont(Fonts.get(10))
        lbl_sw.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_sw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.switch = ToggleSwitch(on_toggle=self._on_mode_toggle)
        sw_col.addWidget(lbl_sw); sw_col.addWidget(self.switch)
        top.addLayout(col); top.addStretch(); top.addLayout(sw_col)
        root.addLayout(top)

        # ── Fila principal: métricas izq + gráfica der ───────
        main_row = QHBoxLayout(); main_row.setSpacing(10)

        left = QVBoxLayout(); left.setSpacing(10)
        self.card_sys = self._metric_card("Sistolica",  "--", "mmHg", Colors.CORAL_400, 150)
        self.card_dia = self._metric_card("Diastolica", "--", "mmHg", Colors.AMBER_400, 150)
        left.addWidget(self.card_sys["w"])
        left.addWidget(self.card_dia["w"])

        self.wave_wrapper = QWidget()
        self.wave_wrapper.setObjectName("wave_wrapper")
        self.wave_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ww_lay = QVBoxLayout(self.wave_wrapper)
        ww_lay.setContentsMargins(0, 0, 0, 0)
        self.waveform = PressureWaveWidget(dark=self.dark)
        ww_lay.addWidget(self.waveform)

        main_row.addLayout(left)
        main_row.addWidget(self.wave_wrapper, stretch=1)
        root.addLayout(main_row, stretch=2)

        # ── Mini gráfica oscilaciones ────────────────────────
        self.osc_wrapper = QWidget()
        self.osc_wrapper.setObjectName("wave_wrapper")
        self.osc_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        osc_lay = QVBoxLayout(self.osc_wrapper)
        osc_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_osc_title = QLabel("  Oscilaciones del pulso")
        self.lbl_osc_title.setFont(Fonts.get(9))
        self.lbl_osc_title.setStyleSheet(f"color:{Colors.SLATE_400};")
        osc_lay.addWidget(self.lbl_osc_title)
        self.osc_wave = OscWaveWidget(dark=self.dark)
        osc_lay.addWidget(self.osc_wave)
        root.addWidget(self.osc_wrapper, stretch=1)

        # ── Fila inferior: MAP + FC + estado + botones ───────
        bottom = QHBoxLayout(); bottom.setSpacing(8)
        self.card_map = self._tiny_card("MAP", "--", "mmHg", Colors.TEAL_500)
        self.card_hr  = self._tiny_card("FC",  "--", "bpm",  Colors.BLUE_400)
        bottom.addWidget(self.card_map["w"])
        bottom.addWidget(self.card_hr["w"])

        self.lbl_phase = QLabel("Listo para medir")
        self.lbl_phase.setFont(Fonts.get(11, QFont.Weight.Medium))
        self.lbl_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_phase.setFixedHeight(44)
        self.lbl_phase.setObjectName("phase_card")
        bottom.addWidget(self.lbl_phase, stretch=1)

        self.btn_measure  = MeasureButton("▶  Medir")
        self.btn_deflate  = MeasureButton("↓  Desinflar")
        self.btn_analysis = MeasureButton("📊  Analisis")
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_deflate.clicked.connect(self._on_deflate)
        self.btn_analysis.clicked.connect(self._on_show_analysis)
        self.btn_analysis.setEnabled(False)
        bottom.addWidget(self.btn_measure)
        bottom.addWidget(self.btn_deflate)
        bottom.addWidget(self.btn_analysis)
        root.addLayout(bottom)

        self._shadow_widgets = [
            self.card_sys["w"], self.card_dia["w"],
            self.card_map["w"], self.card_hr["w"],
            self.wave_wrapper, self.osc_wrapper,
        ]
        self._refresh_shadows()

    def _metric_card(self, title, value, unit, color, width) -> dict:
        w = QWidget(); w.setObjectName("metric_card")
        w.setFixedWidth(width)
        w.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(w); lay.setContentsMargins(14,12,14,12); lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl_t = QLabel(title); lbl_t.setFont(Fonts.get(10))
        lbl_t.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_v = QLabel(value); lbl_v.setFont(Fonts.get(38, QFont.Weight.Medium))
        lbl_v.setStyleSheet(f"color:{color};")
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_u = QLabel(unit); lbl_u.setFont(Fonts.get(12))
        lbl_u.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_u.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(); lay.addWidget(lbl_t); lay.addWidget(lbl_v)
        lay.addWidget(lbl_u); lay.addStretch()
        return {"w": w, "val": lbl_v}

    def _tiny_card(self, title, value, unit, color) -> dict:
        w = QWidget(); w.setObjectName("metric_card")
        w.setFixedHeight(44)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QHBoxLayout(w); lay.setContentsMargins(12,6,12,6); lay.setSpacing(6)
        lbl_t = QLabel(title); lbl_t.setFont(Fonts.get(10))
        lbl_t.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_v = QLabel(value); lbl_v.setFont(Fonts.get(15, QFont.Weight.Medium))
        lbl_v.setStyleSheet(f"color:{color};")
        lbl_u = QLabel(unit); lbl_u.setFont(Fonts.get(10))
        lbl_u.setStyleSheet(f"color:{Colors.SLATE_400};")
        lay.addWidget(lbl_t); lay.addWidget(lbl_v); lay.addWidget(lbl_u); lay.addStretch()
        return {"w": w, "val": lbl_v}

    def _refresh_shadows(self):
        for w in self._shadow_widgets:
            w.setGraphicsEffect(_make_shadow(radius=18, opacity=0.10, dy=3, dark=self.dark))

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(f"""
            PressureWidget2 {{ background:{bg}; }}
            #metric_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            #phase_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:12px; color:{Colors.SLATE_400};
            }}
            #wave_wrapper {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            QLabel {{ color:{text}; background:transparent; }}
            QPushButton {{
                background:{Colors.TEAL_500}; color:#fff;
                border-radius:10px; border:none;
            }}
            QPushButton:hover {{ background:{Colors.TEAL_700}; }}
            QPushButton:disabled {{ background:{Colors.SLATE_400}; color:#aaa; }}
        """)
        self.waveform.set_dark(self.dark)
        self.osc_wave.set_dark(self.dark)
        self._refresh_shadows()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(100)

    def _compute_live_osc(self, ses_p, ses_t):
        if len(ses_p) < _MIN_OSC_SAMPLES:
            return None, None
        p_arr = np.array(ses_p, dtype=float)
        t_arr = np.array(ses_t, dtype=float)
        dur   = t_arr[-1] - t_arr[0]
        fs    = len(t_arr) / dur if dur > 0 else self._live_fs
        self._live_fs = fs
        try:
            osc = filtro_banda(p_arr, fs)
        except Exception:
            return None, None
        from scipy.signal import find_peaks
        dist = max(int(fs * 0.35), 1)
        picos, _ = find_peaks(osc, distance=dist)
        return osc, picos if len(picos) else None

    def _update(self):
        if self.monitor is None:
            return

        phase  = self.monitor.phase
        result = self.monitor.result
        mmhg   = self.monitor.current_mmhg
        t, p   = self.monitor.get_waveform()

        self.waveform.update_data(t, p, phase, result)
        self._update_phase_ui(phase, mmhg, result)

        if result and result != self._last_result:
            self._last_result = result
            self.osc_wave.update_osc(result.get("osc"), result.get("picos"), live=False)
            self.lbl_osc_title.setText("  Oscilaciones del pulso  ✓ medicion completa")
            self.btn_analysis.setEnabled(True)

        elif phase == "deflating":
            ses_t, ses_p = self.monitor.get_session_waveform()
            osc, picos   = self._compute_live_osc(ses_p, ses_t)
            if osc is not None:
                self.osc_wave.update_osc(osc, picos, live=True)
                self.lbl_osc_title.setText("  Oscilaciones del pulso  ● en vivo")

    def _update_phase_ui(self, phase, mmhg, result):
        label, color = PHASE_LABELS.get(phase, ("", Colors.SLATE_400))
        if phase in ("inflating", "deflating"):
            self.lbl_phase.setText(f"{label} {mmhg:.0f} mmHg")
        else:
            self.lbl_phase.setText(label)
        self.lbl_phase.setStyleSheet(
            f"#phase_card {{ background:transparent; border:0.5px solid "
            f"{Colors.DARK_BORDER if self.dark else Colors.LIGHT_BORDER}; "
            f"border-radius:12px; color:{color}; }}"
        )
        if result:
            self.card_sys["val"].setText(f"{result['sys']:.0f}")
            self.card_dia["val"].setText(f"{result['dia']:.0f}")
            self.card_map["val"].setText(f"{result['map']:.0f}")
            self.card_hr["val"].setText(str(result["hr"]))
            self.card_sys["val"].setStyleSheet(f"color:{result['color']};")
            self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        elif phase == "error" and self.monitor:
            self.lbl_phase.setText(f"Error: {self.monitor.error}")
        busy = phase in ("inflating", "deflating", "calculating")
        self.btn_measure.setEnabled(not busy)
        self.btn_measure.setStyleSheet(
            f"background:{Colors.SLATE_400}; color:#fff; border-radius:10px; border:none;"
            if busy else
            f"background:{Colors.TEAL_500}; color:#fff; border-radius:10px; border:none;"
        )

    def _on_measure(self):
        if self.monitor:
            self.btn_analysis.setEnabled(False)
            self._last_result = None
            self.osc_wave.update_osc(None, live=False)
            self.lbl_osc_title.setText("  Oscilaciones del pulso")
            self.monitor.start_measurement()

    def _on_deflate(self):
        if self.monitor:
            self.monitor.deflate()

    def _on_show_analysis(self):
        if not self._last_result:
            return
        dlg = EnvelopeDialog(self._last_result, dark=self.dark, parent=self)
        dlg.exec()

    def _on_mode_toggle(self, dark):
        self.dark = dark
        self._apply_style()
        if self.parent() and hasattr(self.parent(), "set_dark"):
            self.parent().set_dark(dark)

    def set_dark(self, dark):
        self.dark = dark
        self.switch.setChecked(dark)
        self._apply_style()
