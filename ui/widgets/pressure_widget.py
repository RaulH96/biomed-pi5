import numpy as np
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QPushButton, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QPainterPath
)
from ui.theme import Colors, Fonts
from ui.widgets.thermal_widget import ToggleSwitch, _make_shadow
from processing.pressure import filtro_banda

PHASE_LABELS = {
    "idle":        ("Listo para medir", Colors.SLATE_400),
    "inflating":   ("Inflando...",      Colors.AMBER_400),
    "deflating":   ("Midiendo...",      Colors.BLUE_400),
    "calculating": ("Calculando...",    Colors.TEAL_500),
    "done":        ("Medicion lista",   Colors.GREEN_400),
    "error":       ("Error",            Colors.CORAL_400),
}

# Mínimo de muestras para intentar filtrar en vivo
_MIN_OSC_SAMPLES = 64


class PressureWaveWidget(QWidget):
    """Grafica principal — presion en mmHg en vivo."""
    WINDOW_S = 60

    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark    = dark
        self._t      = []
        self._p      = []
        self._phase  = "idle"
        self._result = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(120)

    def update_data(self, t, p, phase, result=None):
        self._t = t; self._p = p
        self._phase = phase; self._result = result
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width(); h = self.height()
        bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        p.fillRect(0, 0, w, h, QColor(bg))

        if len(self._p) < 10:
            p.setPen(QColor(Colors.SLATE_400))
            p.setFont(Fonts.get(11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Presiona Medir para iniciar")
            p.end(); return

        t_arr = np.array(self._t); p_arr = np.array(self._p)
        if t_arr[-1] > self.WINDOW_S:
            mask  = t_arr >= t_arr[-1] - self.WINDOW_S
            t_arr = t_arr[mask]; p_arr = p_arr[mask]

        t_min = t_arr[0]; t_rng = max(t_arr[-1] - t_min, 1)
        p_min = 0; p_max = 220

        def sx(v): return (v - t_min) / t_rng * (w - 20) + 10
        def sy(v): return h - 10 - (v - p_min) / (p_max - p_min) * (h - 20)

        grid_pen = QPen(QColor(Colors.SLATE_200 if not self.dark else Colors.DARK_BORDER),
                        0.5, Qt.PenStyle.DashLine)
        p.setFont(Fonts.get(9))
        for mmhg in [40, 80, 120, 160, 200]:
            y = sy(mmhg)
            p.setPen(grid_pen)
            p.drawLine(10, int(y), w - 10, int(y))
            p.setPen(QColor(Colors.SLATE_400))
            p.drawText(2, int(y) + 4, str(mmhg))

        path = QPainterPath()
        for i, (tv, pv) in enumerate(zip(t_arr, p_arr)):
            x, y = sx(tv), sy(pv)
            if i == 0: path.moveTo(x, y)
            else:      path.lineTo(x, y)

        accent = Colors.AMBER_400 if self._phase == "inflating" else Colors.BLUE_400
        p.setPen(QPen(QColor(accent), 1.5, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)

        if self._result:
            for val, color, label in [
                (self._result["sys"], Colors.CORAL_400, f"SYS {self._result['sys']:.0f}"),
                (self._result["dia"], Colors.AMBER_400, f"DIA {self._result['dia']:.0f}"),
                (self._result["map"], Colors.TEAL_500,  f"MAP {self._result['map']:.0f}"),
            ]:
                y = sy(val)
                p.setPen(QPen(QColor(color), 1.2, Qt.PenStyle.DashLine))
                p.drawLine(10, int(y), w - 10, int(y))
                p.setPen(QColor(color))
                p.setFont(Fonts.get(9))
                p.drawText(w - 62, int(y) - 2, label)
        p.end()

    def set_dark(self, dark):
        self.dark = dark; self.update()


class OscWaveWidget(QWidget):
    """Mini grafica — oscilaciones filtradas del pulso (vivo o post-medicion)."""
    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark   = dark
        self._osc   = np.array([])
        self._picos = np.array([], dtype=int)
        self._live  = False          # True = actualizacion en vivo
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(70)

    def update_osc(self, osc, picos=None, live=False):
        """
        osc   : array de la señal filtrada
        picos : índices de picos detectados (opcional)
        live  : si True muestra indicador de 'en vivo'
        """
        self._osc   = np.array(osc)   if osc   is not None else np.array([])
        self._picos = np.array(picos, dtype=int) if picos is not None else np.array([], dtype=int)
        self._live  = live
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width(); h = self.height()
        bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        p.fillRect(0, 0, w, h, QColor(bg))

        if len(self._osc) < 10:
            p.setPen(QColor(Colors.SLATE_400))
            p.setFont(Fonts.get(9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Oscilaciones — disponible durante y tras la medicion")
            p.end(); return

        osc = self._osc
        mn  = osc.min(); mx = osc.max()
        rng = max(mx - mn, 0.1)
        n   = len(osc)
        step = w / max(n - 1, 1)

        def sx(i): return i * step
        def sy(v): return h - 4 - ((v - mn) / rng) * (h - 8)

        # Linea cero
        y0 = sy(0) if mn < 0 < mx else sy(mn + rng / 2)
        p.setPen(QPen(QColor(Colors.SLATE_400), 0.5, Qt.PenStyle.DashLine))
        p.drawLine(0, int(y0), w, int(y0))

        # Señal oscilometrica
        path = QPainterPath()
        for i, v in enumerate(osc):
            x, y = sx(i), sy(v)
            if i == 0: path.moveTo(x, y)
            else:      path.lineTo(x, y)

        line_color = Colors.AMBER_400 if self._live else Colors.GREEN_400
        p.setPen(QPen(QColor(line_color), 1.2,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(path)

        # Picos detectados
        if len(self._picos):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(Colors.CORAL_400)))
            for pi in self._picos:
                if 0 <= pi < n:
                    x = sx(pi); y = sy(osc[pi])
                    p.drawEllipse(int(x)-3, int(y)-3, 6, 6)

        # Indicador LIVE
        if self._live:
            p.setBrush(QBrush(QColor(Colors.AMBER_400)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(w - 12, 6, 7, 7)
            p.setPen(QColor(Colors.AMBER_400))
            p.setFont(Fonts.get(8))
            p.drawText(w - 34, 14, "LIVE")

        p.end()

    def set_dark(self, dark):
        self.dark = dark; self.update()


class EnvelopeDialog(QDialog):
    """Ventana con la envolvente oscilometrica completa."""
    def __init__(self, result, dark=False, parent=None):
        super().__init__(parent)
        self.result = result
        self.dark   = dark
        self.setWindowTitle("Analisis oscilometrico")
        self.setMinimumSize(700, 480)
        self._build()

    def _build(self):
        # ── Fix: crear Figure ANTES de intentar desempacar subplots ──
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        bg_fig  = "#1e1e2e" if self.dark else "#F7F8FA"
        bg_axes = "#1e1e2e" if self.dark else "#FFFFFF"
        tc      = "white"   if self.dark else "#2E3240"
        gc      = "#333"    if self.dark else "#CDD0D8"

        # Crear figura correctamente
        fig = Figure(figsize=(10, 6), facecolor=bg_fig)
        a1  = fig.add_subplot(211)
        a2  = fig.add_subplot(212)

        res = self.result
        for ax in [a1, a2]:
            ax.set_facecolor(bg_axes)
            ax.tick_params(colors=tc)
            for sp in ax.spines.values(): sp.set_color(gc)
            ax.grid(True, color=gc, linewidth=0.5, alpha=0.5)
            ax.yaxis.label.set_color(tc)
            ax.xaxis.label.set_color(tc)
            ax.title.set_color(tc)

        # Panel 1 — señal completa
        a1.plot(res["t_arr"], res["p_arr"], color="#4AAADE", linewidth=0.8, label="Presion")
        for val, col, lbl in [
            (res["sys"], "#E8845A", f"Sistolica {res['sys']:.0f} mmHg"),
            (res["dia"], "#F0A830", f"Diastolica {res['dia']:.0f} mmHg"),
            (res["map"], "#2A9080", f"MAP {res['map']:.0f} mmHg"),
        ]:
            a1.axhline(val, color=col, linestyle="-.", linewidth=1.2, label=lbl)
        a1.set_ylabel("Presion (mmHg)")
        a1.set_title("Senal completa de la sesion")
        a1.legend(facecolor=bg_axes, labelcolor=tc, fontsize=8)

        # Panel 2 — envolvente oscilometrica
        a2.plot(res["p_picos"], res["env"], color="#E8845A",
                linewidth=1.5, marker="o", markersize=4, label="Envolvente")
        for idx, col, lbl in [
            (res["idx_sys"], "#E8845A", f"SYS crudo {res['sys_crudo']:.0f}→{res['sys']:.0f}"),
            (res["idx_max"], "#2A9080", f"MAP {res['map']:.0f}"),
            (res["idx_dia"], "#F0A830", f"DIA crudo {res['dia_crudo']:.0f}→{res['dia']:.0f}"),
        ]:
            if idx is not None and 0 <= idx < len(res["p_picos"]):
                a2.axvline(res["p_picos"][idx], color=col, linestyle="--",
                           linewidth=1.2, label=lbl)
        a2.set_xlabel("Presion en el pico (mmHg)")
        a2.set_ylabel("Amplitud oscilacion")
        a2.set_title("Envolvente oscilometrica — deteccion SYS / MAP / DIA")
        a2.legend(facecolor=bg_axes, labelcolor=tc, fontsize=8)

        fig.tight_layout()
        canvas = FigureCanvas(fig)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(canvas)

        btn = QPushButton("Cerrar")
        btn.setFixedHeight(36)
        btn.clicked.connect(self.close)
        btn.setStyleSheet(
            f"background:{Colors.TEAL_500}; color:#fff; border-radius:8px; border:none;"
        )
        lay.addWidget(btn)


class MeasureButton(QPushButton):
    def __init__(self, label="Medir", parent=None):
        super().__init__(label, parent)
        self.setFixedHeight(44)
        self.setFont(Fonts.get(13, QFont.Weight.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class PressureWidget(QWidget):
    def __init__(self, monitor=None, dark=False, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.dark    = dark
        self._last_result  = None
        self._shadow_widgets = []
        # Fs estimada de la sesion para filtro en vivo
        self._live_fs = 100.0
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

        # ── Métricas SYS + DIA ───────────────────────────────
        metrics_row = QHBoxLayout(); metrics_row.setSpacing(10)
        self.card_sys = self._metric_card("Sistolica",  "--", "mmHg", Colors.CORAL_400)
        self.card_dia = self._metric_card("Diastolica", "--", "mmHg", Colors.AMBER_400)
        metrics_row.addWidget(self.card_sys["w"])
        metrics_row.addWidget(self.card_dia["w"])
        root.addLayout(metrics_row)

        # ── MAP + FC + estado ────────────────────────────────
        sub_row = QHBoxLayout(); sub_row.setSpacing(10)
        self.card_map = self._small_card("MAP", "--", "mmHg", Colors.TEAL_500)
        self.card_hr  = self._small_card("FC",  "--", "bpm",  Colors.BLUE_400)
        sub_row.addWidget(self.card_map["w"])
        sub_row.addWidget(self.card_hr["w"])
        self.lbl_phase = QLabel("Listo para medir")
        self.lbl_phase.setFont(Fonts.get(11, QFont.Weight.Medium))
        self.lbl_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_phase.setFixedHeight(44)
        self.lbl_phase.setObjectName("phase_card")
        sub_row.addWidget(self.lbl_phase, stretch=1)
        root.addLayout(sub_row)

        # ── Grafica presion en vivo ──────────────────────────
        self.wave_wrapper = QWidget()
        self.wave_wrapper.setObjectName("wave_wrapper")
        self.wave_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ww_lay = QVBoxLayout(self.wave_wrapper)
        ww_lay.setContentsMargins(0, 0, 0, 0)
        self.waveform = PressureWaveWidget(dark=self.dark)
        ww_lay.addWidget(self.waveform)
        root.addWidget(self.wave_wrapper, stretch=2)

        # ── Mini grafica oscilaciones ────────────────────────
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

        # ── Botones ──────────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.btn_measure  = MeasureButton("▶  Medir")
        self.btn_deflate  = MeasureButton("↓  Desinflar")
        self.btn_analysis = MeasureButton("📊  Ver analisis")
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_deflate.clicked.connect(self._on_deflate)
        self.btn_analysis.clicked.connect(self._on_show_analysis)
        self.btn_analysis.setEnabled(False)
        btn_row.addWidget(self.btn_measure)
        btn_row.addWidget(self.btn_deflate)
        btn_row.addWidget(self.btn_analysis)
        root.addLayout(btn_row)

        self._shadow_widgets = [
            self.card_sys["w"], self.card_dia["w"],
            self.card_map["w"], self.card_hr["w"],
            self.wave_wrapper, self.osc_wrapper,
        ]
        self._refresh_shadows()

    def _metric_card(self, title, value, unit, color) -> dict:
        w = QWidget(); w.setObjectName("metric_card")
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        w.setFixedHeight(100)
        lay = QVBoxLayout(w); lay.setContentsMargins(16,10,16,10); lay.setSpacing(2)
        lbl_t = QLabel(title); lbl_t.setFont(Fonts.get(10))
        lbl_t.setStyleSheet(f"color:{Colors.SLATE_400};")
        num_row = QHBoxLayout(); num_row.setSpacing(4)
        lbl_v = QLabel(value); lbl_v.setFont(Fonts.get(38, QFont.Weight.Medium))
        lbl_v.setStyleSheet(f"color:{color};")
        lbl_u = QLabel(unit); lbl_u.setFont(Fonts.get(13))
        lbl_u.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_u.setAlignment(Qt.AlignmentFlag.AlignBottom)
        num_row.addWidget(lbl_v); num_row.addWidget(lbl_u); num_row.addStretch()
        lay.addWidget(lbl_t); lay.addLayout(num_row)
        return {"w": w, "val": lbl_v}

    def _small_card(self, title, value, unit, color) -> dict:
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
            PressureWidget {{ background:{bg}; }}
            #metric_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:14px;
            }}
            #phase_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:12px; color:{Colors.SLATE_400};
            }}
            #wave_wrapper {{
                background:{surf}; border:0.5px solid {border};
                border-radius:14px;
            }}
            QLabel {{ color:{text}; background:transparent; }}
            QPushButton {{
                background:{Colors.TEAL_500}; color:#fff;
                border-radius:10px; border:none;
            }}
            QPushButton:hover  {{ background:{Colors.TEAL_700}; }}
            QPushButton:disabled {{ background:{Colors.SLATE_400}; color:#aaa; }}
        """)
        self.waveform.set_dark(self.dark)
        self.osc_wave.set_dark(self.dark)
        self._refresh_shadows()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(100)

    # ── Oscilaciones en vivo ─────────────────────────────────
    def _compute_live_osc(self, ses_p: list, ses_t: list):
        """
        Filtra la señal de sesion en banda y retorna (osc, picos).
        Necesita al menos _MIN_OSC_SAMPLES puntos.
        """
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
        # Picos simples — sin umbral estricto para la vista en vivo
        from scipy.signal import find_peaks
        dist = max(int(fs * 0.35), 1)
        picos, _ = find_peaks(osc, distance=dist)
        return osc, picos if len(picos) else None

    def _update(self):
        if self.monitor is None:
            self._mock_update(); return

        phase  = self.monitor.phase
        result = self.monitor.result
        mmhg   = self.monitor.current_mmhg
        t, p   = self.monitor.get_waveform()
        self.waveform.update_data(t, p, phase, result)
        self._update_phase_ui(phase, mmhg, result)

        # ── Resultado final disponible ───────────────────────
        if result and result != self._last_result:
            self._last_result = result
            self.osc_wave.update_osc(result.get("osc"), result.get("picos"), live=False)
            self.lbl_osc_title.setText("  Oscilaciones del pulso  ✓ medicion completa")
            self.btn_analysis.setEnabled(True)

        # ── Oscilaciones en vivo durante deflacion ───────────
        elif phase == "deflating":
            ses_t, ses_p = self.monitor.get_session_waveform()
            osc, picos   = self._compute_live_osc(ses_p, ses_t)
            if osc is not None:
                self.osc_wave.update_osc(osc, picos, live=True)
                self.lbl_osc_title.setText("  Oscilaciones del pulso  ● en vivo")

    def _mock_update(self):
        t_now = time.time()
        t = [t_now - 60 + i for i in range(200)]
        p = [80 + 70*np.exp(-0.03*i) + np.random.uniform(-1,1) for i in range(200)]
        self.waveform.update_data(t, p, "deflating", None)
        self._update_phase_ui("deflating", p[-1], None)
        osc = np.sin(np.linspace(0, 8*np.pi, 200)) * np.exp(-np.linspace(0,3,200))
        picos = np.array([int(i) for i in np.linspace(10, 190, 8)], dtype=int)
        self.osc_wave.update_osc(osc, picos, live=True)

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
            self.card_sys["val"].setStyleSheet(f"color:{result.get('color', Colors.CORAL_400)};")
            self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        elif phase == "error" and self.monitor:
            self.lbl_phase.setText(f"Error: {self.monitor.error}")
        busy = phase in ("inflating", "deflating", "calculating")
        self.btn_measure.setEnabled(not busy)

    def _on_measure(self):
        if self.monitor:
            self.btn_analysis.setEnabled(False)
            self._last_result = None
            self.osc_wave.update_osc(None, live=False)
            self.lbl_osc_title.setText("  Oscilaciones del pulso")
            self.monitor.start_measurement()

    def _on_deflate(self):
        if self.monitor: self.monitor.deflate()

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
