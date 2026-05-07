# ui/widgets/welcome_dialog.py
import json
from pathlib import Path
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPainterPath, QPixmap
from ui.theme import Colors, Fonts
from ui.widgets.patient_widget import AvatarWidget

PATIENT_FILE = Path("config/patient.json")
DB_PATH      = Path("data/biomed.db")


def _last_session_str(patient_uuid: str) -> str:
    """Retorna texto tipo 'Última sesión: hace 2 días' o ''"""
    if not DB_PATH.exists():
        return ""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        row  = conn.execute(
            "SELECT MAX(started_at) FROM sessions WHERE patient_id=?",
            (patient_uuid,)
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return "Primera sesión"
        ts   = row[0]
        diff = datetime.now().timestamp() - ts
        if diff < 3600:
            return "Última sesión: hace menos de 1 hora"
        elif diff < 86400:
            h = int(diff / 3600)
            return f"Última sesión: hace {h} hora{'s' if h>1 else ''}"
        else:
            d = int(diff / 86400)
            return f"Última sesión: hace {d} día{'s' if d>1 else ''}"
    except Exception:
        return ""


class WelcomeDialog(QDialog):
    """
    Resultado:
      .choice = 'continue' | 'change' | 'anonymous'
    """
    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.choice = "anonymous"
        self.dark   = dark
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(340)
        self._build()

    def _build(self):
        # Cargar datos del paciente
        self._patient = {}
        if PATIENT_FILE.exists():
            try:
                self._patient = json.loads(PATIENT_FILE.read_text())
            except Exception:
                pass

        name         = self._patient.get("name", "")
        patient_uuid = self._patient.get("uuid", "")
        last_sess    = _last_session_str(patient_uuid) if patient_uuid else ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("welcome_card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(28, 28, 28, 24)
        card_lay.setSpacing(16)

        # Avatar + nombre
        top = QHBoxLayout()
        top.setSpacing(16)

        avatar = AvatarWidget()
        avatar.set_photo(self._patient.get("photo", ""))
        avatar.set_initials(name or "?")
        top.addWidget(avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if name:
            lbl_hello = QLabel(f"Hola de nuevo,")
            lbl_hello.setFont(Fonts.get(13))
            lbl_hello.setStyleSheet(f"color:{Colors.SLATE_400};")

            lbl_name = QLabel(name)
            lbl_name.setFont(Fonts.get(20, QFont.Weight.Medium))
            lbl_name.setStyleSheet(
                f"color:{Colors.DARK_TEXT if self.dark else Colors.LIGHT_TEXT};"
            )
            info_col.addWidget(lbl_hello)
            info_col.addWidget(lbl_name)
        else:
            lbl_hello = QLabel("Sin paciente registrado")
            lbl_hello.setFont(Fonts.get(15, QFont.Weight.Medium))
            info_col.addWidget(lbl_hello)

        if last_sess:
            lbl_last = QLabel(last_sess)
            lbl_last.setFont(Fonts.get(11))
            lbl_last.setStyleSheet(f"color:{Colors.SLATE_400};")
            info_col.addWidget(lbl_last)

        top.addLayout(info_col)
        top.addStretch()
        card_lay.addLayout(top)

        # UUID pequeño
        if patient_uuid:
            lbl_uuid = QLabel(f"ID: {patient_uuid[:8]}...")
            lbl_uuid.setFont(Fonts.get(9))
            lbl_uuid.setStyleSheet(f"color:{Colors.SLATE_400};")
            card_lay.addWidget(lbl_uuid)

        # Botones
        if name:
            btn_continue = self._btn(
                f"✓  Continuar como {name.split()[0]}",
                Colors.TEAL_500, "#FFFFFF"
            )
            btn_continue.clicked.connect(self._on_continue)
            card_lay.addWidget(btn_continue)

        btn_change = self._btn(
            "👤  Cambiar paciente",
            Colors.SLATE_100, Colors.SLATE_600
        )
        btn_change.clicked.connect(self._on_change)
        card_lay.addWidget(btn_change)

        btn_anon = self._btn(
            "→  Sesión anónima",
            "transparent", Colors.SLATE_400
        )
        btn_anon.clicked.connect(self._on_anonymous)
        card_lay.addWidget(btn_anon)

        outer.addWidget(card)

        # Estilo del card
        bg   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        text = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        card.setStyleSheet(f"""
            #welcome_card {{
                background: {bg};
                border-radius: 20px;
            }}
            QLabel {{ color: {text}; background: transparent; }}
        """)

    def _btn(self, text: str, bg: str, fg: str) -> QPushButton:
        from PyQt6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setFont(Fonts.get(13, QFont.Weight.Medium))
        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:10px; border:none;"
        )
        return btn

    def _on_continue(self):
        self.choice = "continue"
        self.accept()

    def _on_change(self):
        self.choice = "change"
        self.accept()

    def _on_anonymous(self):
        self.choice = "anonymous"
        self.accept()
