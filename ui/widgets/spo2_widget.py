import numpy as np
import time
from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QPainterPath, QLinearGradient
)
from ui.theme import Colors, Fonts, state_badge_style
from ui.widgets.thermal_widget import StatCard, ToggleSwitch, _make_shadow


def classify_spo2(spo2: float) -> tuple[str, str]:
    if spo2 >= 95:
        return "Normal", Colors.GREEN_400
    elif spo2 >= 90:
        return "Bajo", Colors.AMBER_400
    else:
        return "Crítico", Colors.CORAL_400

def classify_bpm(bpm: int) -> tuple[str, str]:
    if bpm == 0:
        return "Sin señal", Colors.SLATE_400
    elif bpm < 50:
        return "Bradicardia", Colors.BLUE_400
    elif bpm <= 100:
        return "Normal", Colors.GREEN_400
    elif bpm <= 120:
        return "Elevado", Colors.AMBER_400
    else:
        return "Taquicardia", Colors.CORAL_400


class WaveformWidget(QWidget):
    """
    Dibuja señal IR + umbral alto (verde punteado) + umbral bajo (amber punteado)
    exactamente como el monitor original pero integrado al tema visual.
    """
    HISTORY = 150

    def __init__(self, dark=False, show_thresholds=True, parent=None):
        super().__init__(parent)
        self.dark             = dark
        self.show_thresholds  = show_thresholds
        self._data       = deque(maxlen=self.HISTORY)
        self._thresh_high= deque(maxlen=self.HISTORY)
        self._thresh_low = deque(maxlen=self.HISTORY)
        self._beat       = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)

    def push(self, ir: float, thresh_high: float = 0,
             thresh_low: float = 0, beat: bool = False):
        self._data.append(ir)
        self._thresh_high.append(thresh_high)
        self._thresh_low.append(thresh_low)
        self._beat = beat
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        p.fillRect(0, 0, w, h, QColor(bg))

        data  = list(self._data)
        high  = list(self._thresh_high)
        low   = list(self._thresh_low)
        valid = [v for v in data if v > 1000]

        if len(valid) < 10:
            p.setPen(QColor(Colors.SLATE_400))
            p.setFont(Fonts.get(11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Coloca el dedo en el sensor")
            p.end()
            return

        mn  = min(valid)
        mx  = max(valid)
        rng = max(mx - mn, 100)
        pad = rng * 0.12

        def scale(v):
            return h - ((v - mn + pad) / (rng + 2 * pad)) * (h - 8) - 4

        step = w / (self.HISTORY - 1)

        # ── Señal principal ───────────────────────────────
        accent = Colors.CORAL_400
        path   = QPainterPath()
        started = False
        for i, v in enumerate(data):
            x = i * step
            y = scale(v) if v > 1000 else scale(mn)
            if not started:
                path.moveTo(x, y)
                started = True
            else:
                path.lineTo(x, y)

        # Gradiente relleno
        grad = QLinearGradient(0, 0, 0, h)
        c1   = QColor(accent); c1.setAlphaF(0.20)
        c2   = QColor(accent); c2.setAlphaF(0.0)
        grad.setColorAt(0, c1); grad.setColorAt(1, c2)
        fill = QPainterPath(path)
        fill.lineTo(w, h); fill.lineTo(0, h); fill.closeSubpath()
        p.fillPath(fill, QBrush(grad))

        pen = QPen(QColor(accent), 2.0, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)

        # ── Umbrales (solo si están activos y show_thresholds=True) ──
        if self.show_thresholds and max(high) > 1000:

            # Umbral alto — verde punteado
            path_high = QPainterPath()
            for i, v in enumerate(high):
                x = i * step
                y = scale(v) if v > 0 else scale(mn)
                if i == 0: path_high.moveTo(x, y)
                else:       path_high.lineTo(x, y)

            pen_high = QPen(QColor(Colors.GREEN_400), 1.2,
                            Qt.PenStyle.DashLine)
            pen_high.setDashPattern([4, 4])
            p.setPen(pen_high)
            p.drawPath(path_high)

            # Umbral bajo — amber punteado
            path_low = QPainterPath()
            for i, v in enumerate(low):
                x = i * step
                y = scale(v) if v > 0 else scale(mn)
                if i == 0: path_low.moveTo(x, y)
                else:       path_low.lineTo(x, y)

            pen_low = QPen(QColor(Colors.AMBER_400), 1.2,
                           Qt.PenStyle.DashLine)
            pen_low.setDashPattern([4, 4])
            p.setPen(pen_low)
            p.drawPath(path_low)

            # Leyenda minimalista
            p.setFont(Fonts.get(9))
            p.setPen(QColor(Colors.GREEN_400))
            p.drawText(4, 12, "▲ umbral alto")
            p.setPen(QColor(Colors.AMBER_400))
            p.drawText(4, 24, "▼ umbral bajo")

        p.end()

    def set_dark(self, dark: bool):
        self.dark = dark
        self.update()

    def toggle_thresholds(self, show: bool):
        self.show_thresholds = show
        self.update()


class SpO2Widget(QWidget):
    def __init__(self, monitor=None, dark=False, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.dark    = dark
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

        # Botón toggle umbrales
        self.btn_thresh = QLabel("Umbrales ●")
        self.btn_thresh.setFont(Fonts.get(10))
        self.btn_thresh.setStyleSheet(f"color:{Colors.GREEN_400}; cursor:pointer;")
        self.btn_thresh.mousePressEvent = lambda e: self._toggle_thresholds()
        self._show_thresholds = True
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

        # ── Métricas SpO2 + BPM ──────────────────────────────
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        self.card_spo2 = self._metric_card(
            "SpO2", "--", "%", Colors.BLUE_400, "spo2"
        )
        self.card_bpm  = self._metric_card(
            "Pulso", "--", "bpm", Colors.CORAL_400, "bpm"
        )
        metrics_row.addWidget(self.card_spo2["widget"])
        metrics_row.addWidget(self.card_bpm["widget"])
        root.addLayout(metrics_row)

        # ── Waveform ─────────────────────────────────────────
        self.wave_wrapper = QWidget()
        self.wave_wrapper.setObjectName("wave_wrapper")
        self.wave_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ww_lay = QVBoxLayout(self.wave_wrapper)
        ww_lay.setContentsMargins(0, 0, 0, 0)
        self.waveform = WaveformWidget(dark=self.dark, show_thresholds=True)
        ww_lay.addWidget(self.waveform)
        root.addWidget(self.wave_wrapper, stretch=1)

        # ── Stats crudos ─────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.card_ir  = StatCard("Señal IR",  "")
        self.card_red = StatCard("Señal Red", "")
        self.card_ir.setFixedHeight(54)
        self.card_red.setFixedHeight(54)
        stats_row.addWidget(self.card_ir)
        stats_row.addWidget(self.card_red)
        root.addLayout(stats_row)

        self._shadow_widgets = [
            self.card_spo2["widget"], self.card_bpm["widget"],
            self.wave_wrapper, self.card_ir, self.card_red
        ]
        self._refresh_shadows()

    def _metric_card(self, title, value, unit, color, key) -> dict:
        w = QWidget()
        w.setObjectName("metric_card")
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        w.setFixedHeight(110)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setFont(Fonts.get(10))
        lbl_title.setStyleSheet(f"color:{Colors.SLATE_400};")

        num_row = QHBoxLayout()
        num_row.setSpacing(4)
        lbl_val = QLabel(value)
        lbl_val.setFont(Fonts.get(42, QFont.Weight.Medium))
        lbl_val.setStyleSheet(f"color:{color};")
        lbl_unit = QLabel(unit)
        lbl_unit.setFont(Fonts.get(13))
        lbl_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_unit.setAlignment(Qt.AlignmentFlag.AlignBottom)
        num_row.addWidget(lbl_val)
        num_row.addWidget(lbl_unit)
        num_row.addStretch()

        lbl_state = QLabel("Sin datos")
        lbl_state.setFont(Fonts.get(11))
        lbl_state.setStyleSheet(f"color:{Colors.SLATE_400};")

        lay.addWidget(lbl_title)
        lay.addLayout(num_row)
        lay.addWidget(lbl_state)

        setattr(self, f"lbl_{key}", lbl_val)
        setattr(self, f"lbl_{key}_state", lbl_state)
        setattr(self, f"color_{key}", color)

        return {"widget": w, "value": lbl_val, "state": lbl_state}

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
            SpO2Widget {{ background:{bg}; }}
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
        amp = 8000
        mn  = 92000
        th  = mn + amp * 0.75
        tl  = mn + amp * 0.60
        beat= np.sin(t * 1.5) > 0.95
        self.waveform.push(ir, thresh_high=th, thresh_low=tl, beat=beat)
        self._render({
            "bpm": 72, "spo2": 97.5,
            "beat_in_progress": beat, "connected": True,
        })
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
