import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor
from ui.theme import Colors, Fonts, state_badge_style


class ToggleSwitch(QWidget):
    def __init__(self, on_toggle=None, parent=None):
        super().__init__(parent)
        self._checked = False
        self._on_toggle = on_toggle
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        self._checked = not self._checked
        self.update()
        if self._on_toggle:
            self._on_toggle(self._checked)

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPainterPath, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor(Colors.TEAL_500) if self._checked else QColor(Colors.SLATE_200)
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 3, 48, 20, 10, 10)
        thumb_x = 26 if self._checked else 2
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(thumb_x, 1, 24, 24)
        p.end()


class StatCard(QWidget):
    def __init__(self, title: str, unit: str = "", dark: bool = False, parent=None):
        super().__init__(parent)
        self.dark = dark
        self._build(title, unit)

    def _build(self, title, unit):
        self.setObjectName("stat_card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(Fonts.get(10))
        self.lbl_title.setStyleSheet(f"color: {Colors.SLATE_400};")

        row = QHBoxLayout()
        row.setSpacing(3)
        self.lbl_value = QLabel("--")
        self.lbl_value.setFont(Fonts.get(15, QFont.Weight.Medium))

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setFont(Fonts.get(11))
        self.lbl_unit.setStyleSheet(f"color: {Colors.SLATE_400};")
        self.lbl_unit.setAlignment(Qt.AlignmentFlag.AlignBottom)

        row.addWidget(self.lbl_value)
        row.addWidget(self.lbl_unit)
        row.addStretch()

        lay.addWidget(self.lbl_title)
        lay.addLayout(row)

    def setValue(self, val: str):
        self.lbl_value.setText(val)

    def setDark(self, dark: bool):
        self.dark = dark
        self._apply_style()

    def _apply_style(self):
        bg = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER if self.dark else Colors.LIGHT_BORDER
        text = Colors.DARK_TEXT if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(
            f"#stat_card {{ background:{bg}; border:0.5px solid {border};"
            f" border-radius:12px; }} QLabel {{ color:{text}; background:transparent; }}"
        )
        self.lbl_title.setStyleSheet(f"color: {Colors.SLATE_400};")
        self.lbl_unit.setStyleSheet(f"color: {Colors.SLATE_400};")


class ThermalWidget(QWidget):

    def __init__(self, driver=None, dark=False, offset=0.7, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.dark   = dark
        self.offset = offset
        self._build_ui()
        self._apply_style()
        self._setup_timer()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Fila superior: título + switch ──────────────────
        top = QHBoxLayout()

        col_title = QVBoxLayout()
        col_title.setSpacing(2)
        lbl_section = QLabel("Sensor térmico")
        lbl_section.setFont(Fonts.get(11))
        lbl_section.setStyleSheet(f"color:{Colors.SLATE_400};")

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("Temperatura corporal")
        title.setFont(Fonts.get(18, QFont.Weight.Medium))

        self.status_dot = QLabel("●")
        self.status_dot.setFont(Fonts.get(9))
        self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400};")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_row.addWidget(title)
        title_row.addWidget(self.status_dot)
        title_row.addStretch()

        col_title.addWidget(lbl_section)
        col_title.addLayout(title_row)

        # Switch modo oscuro
        switch_col = QVBoxLayout()
        switch_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        lbl_switch = QLabel("Oscuro")
        lbl_switch.setFont(Fonts.get(10))
        lbl_switch.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_switch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.switch = ToggleSwitch(on_toggle=self._on_mode_toggle)
        switch_col.addWidget(lbl_switch)
        switch_col.addWidget(self.switch)

        top.addLayout(col_title)
        top.addStretch()
        top.addLayout(switch_col)
        root.addLayout(top)

        # ── Dato principal ───────────────────────────────────
        data_card = QWidget()
        data_card.setObjectName("data_card")
        data_lay = QHBoxLayout(data_card)
        data_lay.setContentsMargins(20, 16, 20, 16)
        data_lay.setSpacing(0)

        left = QVBoxLayout()
        left.setSpacing(6)

        num_row = QHBoxLayout()
        num_row.setSpacing(6)
        self.lbl_temp = QLabel("--.-")
        self.lbl_temp.setFont(Fonts.get(52, QFont.Weight.Medium))
        self.lbl_temp.setStyleSheet(f"color:{Colors.TEAL_500};")

        unit_col = QVBoxLayout()
        unit_col.setAlignment(Qt.AlignmentFlag.AlignBottom)
        lbl_unit = QLabel("°C")
        lbl_unit.setFont(Fonts.get(22))
        lbl_unit.setStyleSheet(f"color:{Colors.SLATE_400};")
        unit_col.addWidget(lbl_unit)
        unit_col.addSpacing(10)

        num_row.addWidget(self.lbl_temp)
        num_row.addLayout(unit_col)
        num_row.addStretch()

        self.lbl_badge = QLabel("Sin datos")
        self.lbl_badge.setFont(Fonts.get(12, QFont.Weight.Medium))
        self.lbl_badge.setFixedHeight(26)
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lbl_badge.setStyleSheet(
            f"background:{Colors.SLATE_100}; color:{Colors.SLATE_600};"
            "border-radius:13px; padding: 0 14px;"
        )

        left.addLayout(num_row)
        left.addWidget(self.lbl_badge)
        data_lay.addLayout(left)
        root.addWidget(data_card)
        self.data_card = data_card

        # ── Mapa de calor ────────────────────────────────────
        pg.setConfigOptions(antialias=True, background=None)
        self.plot = pg.PlotWidget()
        self.plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot.setMinimumHeight(260)
        self.plot.hideAxis("left")
        self.plot.hideAxis("bottom")
        self.plot.getViewBox().setAspectLocked(False)
        self.plot.getViewBox().setDefaultPadding(0)

        self.img_item = pg.ImageItem()
        cmap = pg.colormap.get("inferno", source="matplotlib")
        self.img_item.setColorMap(cmap)
        self.img_item.setLevels([28, 42])
        self.plot.addItem(self.img_item)

        self.colorbar = pg.ColorBarItem(
            values=(28, 42),
            colorMap=cmap,
            label="°C",
            width=14,
            pen=Colors.SLATE_400,
        )
        self.colorbar.setImageItem(self.img_item, insert_in=self.plot.getPlotItem())

        plot_wrapper = QWidget()
        plot_wrapper.setObjectName("plot_wrapper")
        pw_lay = QVBoxLayout(plot_wrapper)
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.addWidget(self.plot)
        root.addWidget(plot_wrapper)
        self.plot_wrapper = plot_wrapper

        # ── Stats inferiores ─────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.card_max     = StatCard("Máx escena",     "°C", self.dark)
        self.card_min     = StatCard("Mín escena",     "°C", self.dark)
        self.card_ambient = StatCard("Ambiente est.",  "°C", self.dark)
        for c in (self.card_max, self.card_min, self.card_ambient):
            c._apply_style()
            stats_row.addWidget(c)
        root.addLayout(stats_row)

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT

        self.setStyleSheet(f"""
            ThermalWidget {{
                background: {bg};
                border-radius: 18px;
            }}
            #data_card {{
                background: {surf};
                border: 0.5px solid {border};
                border-radius: 16px;
            }}
            #plot_wrapper {{
                background: {surf};
                border: 0.5px solid {border};
                border-radius: 16px;
            }}
            QLabel {{
                color: {text};
                background: transparent;
            }}
        """)
        self.plot.setBackground(surf)
        for c in (self.card_max, self.card_min, self.card_ambient):
            c.setDark(self.dark)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(500)

    def _update(self):
        if self.driver is None:
            self._inject_mock()
        else:
            try:
                self._render(self.driver.read_frame())
            except Exception as e:
                self.status_dot.setStyleSheet(f"color:{Colors.CORAL_400}; font-size:9px;")
                self.lbl_badge.setText(f"Error sensor")

    def _inject_mock(self):
        matrix = np.random.uniform(20, 25, (24, 32))
        matrix[6:18, 8:24] = np.random.uniform(35.5, 36.8, (12, 16))
        self._render(matrix)

    def _render(self, matrix: np.ndarray):
        from processing.temperature import (
            get_body_temperature, classify_temperature, get_scene_stats
        )
        self.img_item.setImage(matrix.T, autoLevels=False)

        temp  = get_body_temperature(matrix, offset=self.offset)
        stats = get_scene_stats(matrix)

        if temp is not None:
            state = classify_temperature(temp)
            bg, fg = state_badge_style(state, self.dark)
            self.lbl_temp.setText(f"{temp:.1f}")
            self.lbl_badge.setText(state.replace("_", " ").capitalize())
            self.lbl_badge.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:13px; padding:0 14px;"
            )
            self.status_dot.setStyleSheet(f"color:{Colors.GREEN_400}; font-size:9px;")
        else:
            self.lbl_temp.setText("--.-")
            self.lbl_badge.setText("Sin persona detectada")
            self.lbl_badge.setStyleSheet(
                f"background:{Colors.SLATE_100}; color:{Colors.SLATE_400};"
                "border-radius:13px; padding:0 14px;"
            )

        self.card_max.setValue(f"{stats['max_c']:.1f}")
        self.card_min.setValue(f"{stats['min_c']:.1f}")
        self.card_ambient.setValue(f"{stats['ambient_estimated_c']:.1f}")

    def _on_mode_toggle(self, dark: bool):
        self.dark = dark
        self._apply_style()

    def set_dark(self, dark: bool):
        self.dark = dark
        self.switch._checked = dark
        self.switch.update()
        self._apply_style()
