from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QBrush, QPainterPath, QFont
from ui.theme import Colors, Fonts


class ToastWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity  = 0.0
        self._duration = 3000
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(52)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        self.lbl = QLabel("")
        self.lbl.setFont(Fonts.get(13, QFont.Weight.Medium))
        self.lbl.setStyleSheet("color:#FFFFFF; background:transparent;")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl)

        # Timer para iniciar el fade-out DESPUES de que termina el fade-in
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._start_fade_out)

        # Animacion fade-in
        self._anim_in = QPropertyAnimation(self, b"opacity")
        self._anim_in.setDuration(250)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim_in.finished.connect(self._on_fade_in_done)

        # Animacion fade-out
        self._anim_out = QPropertyAnimation(self, b"opacity")
        self._anim_out.setDuration(300)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InQuad)
        self._anim_out.finished.connect(self._on_fade_out_done)

        self.hide()

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, val):
        self._opacity = max(0.0, min(1.0, val))
        self.update()

    def paintEvent(self, e):
        if self._opacity <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(path, QBrush(QColor("#1C1F2B")))
        p.end()

    def show_message(self, text: str, duration_ms: int = 3000,
                     color: str = None):
        from ui.theme import Colors
        color = color or Colors.GREEN_400

        # Detener animaciones previas
        self._anim_in.stop()
        self._anim_out.stop()
        self._hold_timer.stop()
        self._duration = duration_ms

        self.lbl.setText(text)
        self.lbl.setStyleSheet(f"color:{color}; background:transparent;")

        self.show()
        self.raise_()

        # Fade in desde opacidad actual
        self._anim_in.setStartValue(self._opacity)
        self._anim_in.setEndValue(1.0)
        self._anim_in.start()

    def _on_fade_in_done(self):
        # Esperar el tiempo definido ANTES de iniciar fade-out
        self._hold_timer.start(self._duration)

    def _start_fade_out(self):
        self._anim_out.setStartValue(self._opacity)
        self._anim_out.setEndValue(0.0)
        self._anim_out.start()

    def _on_fade_out_done(self):
        self.hide()
        self._opacity = 0.0
