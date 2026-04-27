import numpy as np
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush,
    QImage, QPixmap
)
from ui.theme import Colors, Fonts, state_badge_style

from processing.temperature import (
            get_body_temperature, classify_temperature, get_scene_stats
        )

# ── Colormap inferno en numpy puro (sin matplotlib) ──────────
def _build_inferno_lut():
    try:
        import matplotlib.cm as cm
        lut = (cm.get_cmap('inferno')(np.linspace(0, 1, 256))[:, :3] * 255).astype(np.uint8)
    except Exception:
        lut = np.zeros((256, 3), dtype=np.uint8)
        for i in range(256):
            t = i / 255.0
            lut[i] = [min(255, int(t * 2 * 255)),
                      min(255, int(max(0, t * 2 - 1) * 255)),
                      max(0, int((1 - t * 1.5) * 80))]
    return lut

_INFERNO_LUT = _build_inferno_lut()


def matrix_to_qpixmap(matrix: np.ndarray, vmin=28.0, vmax=42.0,
                       w: int = 320, h: int = 240) -> QPixmap:
    clipped = np.clip(matrix, vmin, vmax)
    indices = ((clipped - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    rgb = _INFERNO_LUT[indices]                      # (24, 32, 3)
    rows_rep = max(1, (h + 23) // 24)
    cols_rep = max(1, (w + 31) // 32)
    rgb_big = np.repeat(np.repeat(rgb, rows_rep, axis=0), cols_rep, axis=1)
    rgb_big = rgb_big[:h, :w]
    rgb_c = np.ascontiguousarray(rgb_big)
    img = QImage(rgb_c.data, w, h, w * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img)


def _make_shadow(radius=18, opacity=0.13, dx=0, dy=4, dark=False) -> QGraphicsDropShadowEffect:
    sh = QGraphicsDropShadowEffect()
    sh.setBlurRadius(radius)
    sh.setOffset(dx, dy)
    color = QColor(0, 0, 0)
    color.setAlphaF(opacity if not dark else opacity * 0.5)
    sh.setColor(color)
    return sh


class HeatmapWidget(QWidget):
    """Dibuja la matriz térmica con QPainter llenando todo el widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_matrix = None
        self._vmin = 28.0
        self._vmax = 42.0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)

    def setMatrix(self, matrix: np.ndarray, vmin=28.0, vmax=42.0):
        self._last_matrix = matrix
        self._vmin = vmin
        self._vmax = vmax
        self.update()

    def paintEvent(self, e):
        if self._last_matrix is None:
            return
        w = max(self.width(),  1)
        h = max(self.height(), 1)
        # Genera pixmap al tamaño exacto del widget en cada repintado
        pixmap = matrix_to_qpixmap(self._last_matrix, self._vmin, self._vmax, w, h)
        p = QPainter(self)
        p.drawPixmap(0, 0, w, h, pixmap)
        p.end()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.update()


class ToggleSwitch(QWidget):
    def __init__(self, on_toggle=None, parent=None):
        super().__init__(parent)
        self._checked = False
        self._on_toggle = on_toggle
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setChecked(self, val):
        self._checked = val
        self.update()

    def mousePressEvent(self, e):
        self._checked = not self._checked
        self.update()
        if self._on_toggle:
            self._on_toggle(self._checked)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor(Colors.TEAL_500) if self._checked else QColor(Colors.SLATE_200)
        p.setBrush(QBrush(track))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 3, 48, 20, 10, 10)
        thumb_x = 24 if self._checked else 2
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(thumb_x, 1, 24, 24)
        p.end()


class StatCard(QWidget):
    def __init__(self, title, unit="", parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(Fonts.get(10))
        self.lbl_title.setStyleSheet(f"color:{Colors.SLATE_400};")
        row = QHBoxLayout()
        self.lbl_value = QLabel("--")
        self.lbl_value.setFont(Fonts.get(15, QFont.Weight.Medium))
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setFont(Fonts.get(11))
        self.lbl_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        self.lbl_unit.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.lbl_value)
        row.addWidget(self.lbl_unit)
        row.addStretch()
        lay.addWidget(self.lbl_title)
        lay.addLayout(row)

    def setValue(self, val):
        self.lbl_value.setText(val)


class ThermalWidget(QWidget):
    def __init__(self, driver=None, dark=False, offset=0.7, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.dark   = dark
        self.offset = offset
        self._last_matrix = None
        self._shadow_widgets = []
        self._build_ui()
        self._apply_style()
        self._setup_timer()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── Encabezado ───────────────────────────────────────
        top = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl_sub = QLabel("Sensor térmico · MLX90640")
        lbl_sub.setFont(Fonts.get(10))
        lbl_sub.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        lbl_title = QLabel("Temperatura corporal")
        lbl_title.setFont(Fonts.get(18, QFont.Weight.Medium))
        self.status_dot = QLabel("●")
        self.status_dot.setFont(Fonts.get(9))
        self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        title_row.addWidget(lbl_title)
        title_row.addWidget(self.status_dot)
        title_row.addStretch()
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

        # ── Card dato principal — altura fija máxima ─────────
        self.data_card = QWidget()
        self.data_card.setObjectName("data_card")
        self.data_card.setMaximumHeight(110)
        self.data_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        dc_lay = QVBoxLayout(self.data_card)
        dc_lay.setContentsMargins(20, 8, 20, 8)
        dc_lay.setSpacing(4)

        num_row = QHBoxLayout()
        num_row.setSpacing(6)
        num_row.addStretch()
        self.lbl_temp = QLabel("--.-")
        self.lbl_temp.setFont(Fonts.get(48, QFont.Weight.Medium))
        self.lbl_temp.setStyleSheet(f"color:{Colors.TEAL_500};")
        self.lbl_temp.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        uc = QVBoxLayout()
        uc.setAlignment(Qt.AlignmentFlag.AlignBottom)
        lbl_unit = QLabel("°C")
        lbl_unit.setFont(Fonts.get(20))
        lbl_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        uc.addWidget(lbl_unit)
        uc.addSpacing(8)
        num_row.addWidget(self.lbl_temp)
        num_row.addLayout(uc)
        num_row.addStretch()

        badge_row = QHBoxLayout()
        badge_row.addStretch()
        self.lbl_badge = QLabel("Sin datos")
        self.lbl_badge.setFont(Fonts.get(12, QFont.Weight.Medium))
        self.lbl_badge.setFixedHeight(24)
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        badge_row.addWidget(self.lbl_badge)
        badge_row.addStretch()

        dc_lay.addLayout(num_row)
        dc_lay.addLayout(badge_row)
        root.addWidget(self.data_card)

        # ── Heatmap — sin padding para que llene el wrapper ──
        self.plot_wrapper = QWidget()
        self.plot_wrapper.setObjectName("plot_wrapper")
        self.plot_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        pw_lay = QVBoxLayout(self.plot_wrapper)
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.setSpacing(0)
        self.heatmap = HeatmapWidget()
        pw_lay.addWidget(self.heatmap)
        root.addWidget(self.plot_wrapper, stretch=1)

        # ── Stats ────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.card_max     = StatCard("Máx escena",    "°C")
        self.card_min     = StatCard("Mín escena",    "°C")
        self.card_ambient = StatCard("Ambiente est.", "°C")
        for c in (self.card_max, self.card_min, self.card_ambient):
            stats_row.addWidget(c)
        root.addLayout(stats_row)

        self._shadow_widgets = [
            self.data_card, self.plot_wrapper,
            self.card_max, self.card_min, self.card_ambient
        ]
        self._refresh_shadows()

    def _refresh_shadows(self):
        for w in self._shadow_widgets:
            w.setGraphicsEffect(_make_shadow(radius=20, opacity=0.11, dy=4, dark=self.dark))

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(f"""
            ThermalWidget {{ background:{bg}; }}
            #data_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            #plot_wrapper {{
                background:{surf}; border:0.5px solid {border};
                border-radius:16px;
            }}
            #stat_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:12px;
            }}
            QLabel {{ color:{text}; background:transparent; }}
        """)
        self._refresh_shadows()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(250)

    def _update(self):
        if self.driver is None:
            self._inject_mock()
        else:
            try:
                self._render(self.driver.read_frame())
            except Exception:
                self.status_dot.setStyleSheet(f"color:{Colors.CORAL_400};")

    def _inject_mock(self):
  
        t = time.time()
        matrix = np.random.uniform(20, 23, (24, 32))
        cx = int(9 + 4 * np.sin(t * 0.4))
        matrix[4:20, cx:cx+14] = np.random.uniform(35.0, 37.2, (16, 14))
        self._render(matrix)

    def _render(self, matrix):
        
        self._last_matrix = matrix
        self.heatmap.setMatrix(matrix, vmin=28, vmax=42)

        temp  = get_body_temperature(matrix, offset=self.offset)
        stats = get_scene_stats(matrix)

        if temp is not None:
            state = classify_temperature(temp)
            bg, fg = state_badge_style(state, self.dark)
            self.lbl_temp.setText(f"{temp:.1f}")
            self.lbl_badge.setText(state.replace("_", " ").capitalize())
            self.lbl_badge.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:12px; padding:0 14px;"
            )
            self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        else:
            self.lbl_temp.setText("--.-")
            self.lbl_badge.setText("Sin persona detectada")
            self.lbl_badge.setStyleSheet(
                f"background:{Colors.SLATE_100 if not self.dark else Colors.SLATE_800};"
                f"color:{Colors.SLATE_400}; border-radius:12px; padding:0 14px;"
            )

        self.card_max.setValue(f"{stats['max_c']:.1f}")
        self.card_min.setValue(f"{stats['min_c']:.1f}")
        self.card_ambient.setValue(f"{stats['ambient_estimated_c']:.1f}")

    def _on_mode_toggle(self, dark):
        self.dark = dark
        self._apply_style()
        if self.parent() and hasattr(self.parent(), "set_dark"):
            self.parent().set_dark(dark)

    def set_dark(self, dark):
        self.dark = dark
        self.switch.setChecked(dark)
        self._apply_style()