import numpy as np
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush,
    QImage, QPixmap
)
from ui.theme import Colors, Fonts, state_badge_style
from ui.widgets.thermal_widget import (
    HeatmapWidget, ToggleSwitch, StatCard,
    _make_shadow, _build_inferno_lut, matrix_to_qpixmap
)
from processing.temperature import (
    get_body_temperature, classify_temperature, get_scene_stats
)


class ThermalWidget2(QWidget):
    """
    Layout horizontal:
    ┌─────────────────────────────────────────┐
    │  [Temp + badge]  │  [Heatmap]           │
    ├─────────────────────────────────────────┤
    │  Máx   │  Mín   │  Ambiente   │ Switch  │
    └─────────────────────────────────────────┘
    """
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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Encabezado ───────────────────────────────────────
        header = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(1)
        lbl_sub = QLabel("Sensor térmico · MLX90640")
        lbl_sub.setFont(Fonts.get(10))
        lbl_sub.setStyleSheet(f"color:{Colors.SLATE_400};")
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        lbl_title = QLabel("Temperatura corporal")
        lbl_title.setFont(Fonts.get(16, QFont.Weight.Medium))
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

        header.addLayout(col)
        header.addStretch()
        header.addLayout(sw_col)
        root.addLayout(header)

        # ── Fila principal: temp izq + heatmap der ───────────
        main_row = QHBoxLayout()
        main_row.setSpacing(10)

        # Card temperatura — izquierda
        self.data_card = QWidget()
        self.data_card.setObjectName("data_card")
        self.data_card.setFixedWidth(160)
        self.data_card.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        dc_lay = QVBoxLayout(self.data_card)
        dc_lay.setContentsMargins(16, 16, 16, 16)
        dc_lay.setSpacing(8)
        dc_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_temp_label = QLabel("Temp. corporal")
        lbl_temp_label.setFont(Fonts.get(10))
        lbl_temp_label.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_temp = QLabel("--.-")
        self.lbl_temp.setFont(Fonts.get(44, QFont.Weight.Medium))
        self.lbl_temp.setStyleSheet(f"color:{Colors.TEAL_500};")
        self.lbl_temp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_unit = QLabel("°C")
        lbl_unit.setFont(Fonts.get(16))
        lbl_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_badge = QLabel("Sin datos")
        self.lbl_badge.setFont(Fonts.get(11, QFont.Weight.Medium))
        self.lbl_badge.setFixedHeight(24)
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setWordWrap(False)
        self.lbl_badge.setStyleSheet(
            f"background:{Colors.SLATE_100}; color:{Colors.SLATE_600};"
            "border-radius:12px; padding:0 10px;"
        )

        dc_lay.addStretch()
        dc_lay.addWidget(lbl_temp_label)
        dc_lay.addWidget(self.lbl_temp)
        dc_lay.addWidget(lbl_unit)
        dc_lay.addSpacing(8)
        dc_lay.addWidget(self.lbl_badge)
        dc_lay.addStretch()

        # Heatmap — derecha
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

        main_row.addWidget(self.data_card)
        main_row.addWidget(self.plot_wrapper, stretch=1)
        root.addLayout(main_row, stretch=1)

        # ── Stats inferiores ─────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.card_max     = StatCard("Máx escena",    "°C")
        self.card_min     = StatCard("Mín escena",    "°C")
        self.card_ambient = StatCard("Ambiente est.", "°C")
        for c in (self.card_max, self.card_min, self.card_ambient):
            c.setFixedHeight(54)
            stats_row.addWidget(c)
        root.addLayout(stats_row)

        self._shadow_widgets = [
            self.data_card, self.plot_wrapper,
            self.card_max, self.card_min, self.card_ambient
        ]
        self._refresh_shadows()

    def _refresh_shadows(self):
        for w in self._shadow_widgets:
            w.setGraphicsEffect(
                _make_shadow(radius=20, opacity=0.11, dy=4, dark=self.dark)
            )

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(f"""
            ThermalWidget2 {{ background:{bg}; }}
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
                f"background:{bg}; color:{fg}; border-radius:12px; padding:0 10px;"
            )
            self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        else:
            self.lbl_temp.setText("--.-")
            self.lbl_badge.setText("Sin persona")
            self.lbl_badge.setStyleSheet(
                f"background:{Colors.SLATE_100 if not self.dark else Colors.SLATE_800};"
                f"color:{Colors.SLATE_400}; border-radius:12px; padding:0 10px;"
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
  
    def clear_frame(self):
        """Limpiar la imagen térmica al salir del tab"""
        # Poner imagen en negro
        if hasattr(self, '_canvas') and self._canvas:
            from PyQt6.QtGui import QPixmap, QColor
            black_pixmap = QPixmap(self._canvas.size())
            black_pixmap.fill(QColor(0, 0, 0))  # Negro
            self._canvas.setPixmap(black_pixmap)
        
        # Resetear labels
        if hasattr(self, 'lbl_temp'):
            self.lbl_temp.setText("--.-")
        if hasattr(self, 'lbl_badge'):
            self.lbl_badge.setText("Sin persona detectada")
            self.lbl_badge.setStyleSheet(
                f"background:#E4E6EB; color:#555A6A; "
                "border-radius:12px; padding:4px 12px; font-size:11px;"
            )