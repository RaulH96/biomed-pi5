import numpy as np
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.theme import Colors, Fonts
from ui.widgets.thermal_widget import StatCard, ToggleSwitch, _make_shadow
from ui.widgets.spo2_widget import WaveformWidget, classify_spo2, classify_bpm


class SpO2Widget2(QWidget):
    """
    Layout horizontal:
    ┌──────────────┬──────────────────────────┐
    │  SpO2  card  │                          │
    │              │   Waveform + umbrales    │
    │  BPM   card  │                          │
    ├──────────────┴──────────────────────────┤
    │  IR raw  │  Red raw  │  estado          │
    └─────────────────────────────────────────┘
    """
    def __init__(self, monitor=None, dark=False, parent=None):
        super().__init__(parent)
        self.monitor         = monitor
        self.dark            = dark
        self._show_thresholds= True
        self._shadow_widgets = []
        self._build_ui()
        self._apply_style()
        self._setup_timer()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Encabezado ───────────────────────────────────────
        top = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(1)
        lbl_sub = QLabel("Oximetría · MAX30102")
        lbl_sub.setFont(Fonts.get(10))
        lbl_sub.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row = QHBoxLayout()
        lbl_title = QLabel("SpO2 y Pulso")
        lbl_title.setFont(Fonts.get(16, QFont.Weight.Medium))
        self.status_dot = QLabel("●")
        self.status_dot.setFont(Fonts.get(9))
        self.status_dot.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row.addWidget(lbl_title)
        title_row.addWidget(self.status_dot)
        title_row.addStretch()
        self.btn_thresh = QLabel("Umbrales ●")
        self.btn_thresh.setFont(Fonts.get(10))
        self.btn_thresh.setStyleSheet(f"color:{Colors.GREEN_400};")
        self.btn_thresh.mousePressEvent = lambda e: self._toggle_thresholds()
        title_row.addWidget(self.btn_thresh)
        col.addWidget(lbl_sub)
        col.addLayout(title_row)

        sw_col = QVBoxLayout()
        sw_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        lbl_sw = QLabel("Oscuro")
        lbl_sw.setFont(Fonts.get(10))
        lbl_sw.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_sw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.switch = ToggleSwitch(on_toggle=self._on_mode_toggle)
        sw_col.addWidget(lbl_sw)
        sw_col.addWidget(self.switch)

        top.addLayout(col)
        top.addStretch()
        top.addLayout(sw_col)
        root.addLayout(top)

        # ── Fila principal: métricas izq + waveform der ──────
        main_row = QHBoxLayout()
        main_row.setSpacing(10)

        # Columna izquierda — SpO2 arriba, BPM abajo
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Card SpO2
        self.card_spo2 = QWidget()
        self.card_spo2.setObjectName("metric_card")
        self.card_spo2.setFixedWidth(150)
        self.card_spo2.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        spo2_lay = QVBoxLayout(self.card_spo2)
        spo2_lay.setContentsMargins(14, 12, 14, 12)
        spo2_lay.setSpacing(4)
        spo2_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_spo2_title = QLabel("SpO2")
        lbl_spo2_title.setFont(Fonts.get(10))
        lbl_spo2_title.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_spo2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_spo2 = QLabel("--")
        self.lbl_spo2.setFont(Fonts.get(38, QFont.Weight.Medium))
        self.lbl_spo2.setStyleSheet(f"color:{Colors.BLUE_400};")
        self.lbl_spo2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_spo2_unit = QLabel("%")
        lbl_spo2_unit.setFont(Fonts.get(14))
        lbl_spo2_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_spo2_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_spo2_state = QLabel("Sin datos")
        self.lbl_spo2_state.setFont(Fonts.get(10, QFont.Weight.Medium))
        self.lbl_spo2_state.setStyleSheet(f"color:{Colors.SLATE_400};")
        self.lbl_spo2_state.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spo2_lay.addStretch()
        spo2_lay.addWidget(lbl_spo2_title)
        spo2_lay.addWidget(self.lbl_spo2)
        spo2_lay.addWidget(lbl_spo2_unit)
        spo2_lay.addSpacing(4)
        spo2_lay.addWidget(self.lbl_spo2_state)
        spo2_lay.addStretch()

        # Card BPM
        self.card_bpm = QWidget()
        self.card_bpm.setObjectName("metric_card")
        self.card_bpm.setFixedWidth(150)
        self.card_bpm.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        bpm_lay = QVBoxLayout(self.card_bpm)
        bpm_lay.setContentsMargins(14, 12, 14, 12)
        bpm_lay.setSpacing(4)
        bpm_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_bpm_title = QLabel("Pulso")
        lbl_bpm_title.setFont(Fonts.get(10))
        lbl_bpm_title.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_bpm_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_bpm = QLabel("--")
        self.lbl_bpm.setFont(Fonts.get(38, QFont.Weight.Medium))
        self.lbl_bpm.setStyleSheet(f"color:{Colors.CORAL_400};")
        self.lbl_bpm.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_bpm_unit = QLabel("bpm")
        lbl_bpm_unit.setFont(Fonts.get(12))
        lbl_bpm_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_bpm_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_bpm_state = QLabel("Sin datos")
        self.lbl_bpm_state.setFont(Fonts.get(10, QFont.Weight.Medium))
        self.lbl_bpm_state.setStyleSheet(f"color:{Colors.SLATE_400};")
        self.lbl_bpm_state.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bpm_lay.addStretch()
        bpm_lay.addWidget(lbl_bpm_title)
        bpm_lay.addWidget(self.lbl_bpm)
        bpm_lay.addWidget(lbl_bpm_unit)
        bpm_lay.addSpacing(4)
        bpm_lay.addWidget(self.lbl_bpm_state)
        bpm_lay.addStretch()

        left_col.addWidget(self.card_spo2)
        left_col.addWidget(self.card_bpm)

        # Waveform derecha
        self.wave_wrapper = QWidget()
        self.wave_wrapper.setObjectName("wave_wrapper")
        self.wave_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ww_lay = QVBoxLayout(self.wave_wrapper)
        ww_lay.setContentsMargins(0, 0, 0, 0)
        self.waveform = WaveformWidget(dark=self.dark, show_thresholds=True)
        ww_lay.addWidget(self.waveform)

        main_row.addLayout(left_col)
        main_row.addWidget(self.wave_wrapper, stretch=1)
        root.addLayout(main_row, stretch=1)

        # ── Stats inferiores ─────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.card_ir  = StatCard("Señal IR",  "")
        self.card_red = StatCard("Señal Red", "")
        self.card_ir.setFixedHeight(50)
        self.card_red.setFixedHeight(50)
        stats_row.addWidget(self.card_ir)
        stats_row.addWidget(self.card_red)
        root.addLayout(stats_row)

        self._shadow_widgets = [
            self.card_spo2, self.card_bpm,
            self.wave_wrapper, self.card_ir, self.card_red
        ]
        self._refresh_shadows()

    def _refresh_shadows(self):
        for w in self._shadow_widgets:
            w.setGraphicsEffect(
                _make_shadow(radius=18, opacity=0.10, dy=3, dark=self.dark)
            )

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(f"""
            SpO2Widget2 {{ background:{bg}; }}
            #metric_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            #wave_wrapper {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            #stat_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:12px;
            }}
            QLabel {{ color:{text}; background:transparent; }}
        """)
        self.waveform.set_dark(self.dark)
        self._refresh_shadows()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(33)

    def _update(self):
        if self.monitor is None:
            self._inject_mock()
            return
        result = self.monitor.update()
        if result:
            self._render(result)
            self.waveform.push(
                self.monitor.current_ir,
                thresh_high=self.monitor.thresh_high,
                thresh_low =self.monitor.thresh_low,
                beat       =self.monitor.beat_in_progress,
            )
            self.card_ir.setValue(f"{int(self.monitor.current_ir):,}")
            self.card_red.setValue(f"{int(self.monitor.current_red):,}")

    def _inject_mock(self):
        t   = time.time()
        ir  = 100000 + 8000 * np.sin(t * 1.5) + np.random.uniform(-200, 200)
        amp = 8000; mn = 92000
        th  = mn + amp * 0.75
        tl  = mn + amp * 0.60
        beat= np.sin(t * 1.5) > 0.95
        self.waveform.push(ir, thresh_high=th, thresh_low=tl, beat=beat)
        self._render({"bpm": 72, "spo2": 97.5, "beat_in_progress": beat, "connected": True})
        self.card_ir.setValue(f"{int(ir):,}")
        self.card_red.setValue("--")

    def _render(self, data: dict):
        bpm  = data["bpm"]
        spo2 = data["spo2"]
        beat = data["beat_in_progress"]

        if spo2 > 0:
            estado, color = classify_spo2(spo2)
            self.lbl_spo2.setText(f"{spo2:.1f}")
            self.lbl_spo2.setStyleSheet(f"color:{color};")
            self.lbl_spo2_state.setText(estado)
            self.lbl_spo2_state.setStyleSheet(f"color:{color};")
        else:
            self.lbl_spo2.setText("--")
            self.lbl_spo2_state.setText("Sin datos")
            self.lbl_spo2_state.setStyleSheet(f"color:{Colors.SLATE_400};")

        if bpm > 0:
            estado, color = classify_bpm(bpm)
            self.lbl_bpm.setText(str(bpm))
            self.lbl_bpm.setStyleSheet(f"color:{color};")
            self.lbl_bpm_state.setText(estado)
            self.lbl_bpm_state.setStyleSheet(f"color:{color};")
            self.status_dot.setStyleSheet(
                f"color:{Colors.CORAL_400}; font-size:9px;"
                if beat else f"color:{Colors.GREEN_400}; font-size:9px;"
            )
        else:
            self.lbl_bpm.setText("--")
            self.lbl_bpm_state.setText("Sin señal")
            self.lbl_bpm_state.setStyleSheet(f"color:{Colors.SLATE_400};")
            self.status_dot.setStyleSheet(f"color:{Colors.SLATE_400};")

    def _toggle_thresholds(self):
        self._show_thresholds = not self._show_thresholds
        self.waveform.toggle_thresholds(self._show_thresholds)
        color = Colors.GREEN_400 if self._show_thresholds else Colors.SLATE_400
        self.btn_thresh.setStyleSheet(f"color:{color};")

    def _on_mode_toggle(self, dark):
        self.dark = dark
        self._apply_style()
        if self.parent() and hasattr(self.parent(), "set_dark"):
            self.parent().set_dark(dark)

    def set_dark(self, dark):
        self.dark = dark
        self.switch.setChecked(dark)
        self._apply_style()
