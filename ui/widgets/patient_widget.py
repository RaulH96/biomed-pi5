# ui/widgets/patient_widget.py
import yaml
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFileDialog,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPainterPath
from ui.theme import Colors, Fonts
from ui.widgets.thermal_widget import ToggleSwitch, _make_shadow

PATIENT_FILE = Path("config/patient.json")


def _load_patient() -> dict:
    if PATIENT_FILE.exists():
        try:
            return json.loads(PATIENT_FILE.read_text())
        except Exception:
            pass
    return {
        "name": "", "age": "", "phone": "",
        "conditions": "", "medications": "", "allergies": "",
        "photo": "", "notes": "",
    }


def _save_patient(data: dict):
    PATIENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PATIENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


class AvatarWidget(QWidget):
    """Muestra foto circular del paciente o iniciales."""
    SIZE = 96

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._pixmap = None
        self._initials = "?"

    def set_photo(self, path: str):
        if path and Path(path).exists():
            px = QPixmap(path).scaled(
                self.SIZE, self.SIZE,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self._pixmap = px
        else:
            self._pixmap = None
        self.update()

    def set_initials(self, name: str):
        parts = name.strip().split()
        if len(parts) >= 2:
            self._initials = parts[0][0].upper() + parts[-1][0].upper()
        elif parts:
            self._initials = parts[0][0].upper()
        else:
            self._initials = "?"
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.SIZE
        path = QPainterPath()
        path.addEllipse(0, 0, s, s)
        p.setClipPath(path)

        if self._pixmap:
            p.drawPixmap(0, 0, s, s, self._pixmap)
        else:
            p.fillRect(0, 0, s, s, QColor(Colors.TEAL_500))
            p.setPen(QColor("#FFFFFF"))
            font = QFont("Inter"); font.setPixelSize(32); font.setWeight(QFont.Weight.Medium)
            p.setFont(font)
            p.drawText(0, 0, s, s, Qt.AlignmentFlag.AlignCenter, self._initials)
        p.end()


class FieldCard(QWidget):
    """Card con label + input."""
    def __init__(self, label: str, placeholder: str = "",
                 multiline: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("field_card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setFont(Fonts.get(10))
        lbl.setStyleSheet(f"color:{Colors.SLATE_400};")
        lay.addWidget(lbl)

        if multiline:
            self.input = QTextEdit()
            self.input.setPlaceholderText(placeholder)
            self.input.setFont(Fonts.get(13))
            self.input.setFixedHeight(70)
        else:
            self.input = QLineEdit()
            self.input.setPlaceholderText(placeholder)
            self.input.setFont(Fonts.get(13))

        self.input.setStyleSheet(
            "background: transparent; border: none; color: inherit;"
        )
        lay.addWidget(self.input)

    def value(self) -> str:
        if isinstance(self.input, QTextEdit):
            return self.input.toPlainText()
        return self.input.text()

    def set_value(self, v: str):
        if isinstance(self.input, QTextEdit):
            self.input.setPlainText(v)
        else:
            self.input.setText(v)


class PatientWidget(QWidget):
    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark  = dark
        self._data = _load_patient()
        self._photo_path = self._data.get("photo", "")
        self._shadow_widgets = []
        self._build_ui()
        self._apply_style()
        self._load_into_fields()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Encabezado ───────────────────────────────────────
        top = QHBoxLayout()
        col = QVBoxLayout(); col.setSpacing(1)
        lbl_sub = QLabel("Expediente del paciente")
        lbl_sub.setFont(Fonts.get(10))
        lbl_sub.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_title = QLabel("Datos del paciente")
        lbl_title.setFont(Fonts.get(16, QFont.Weight.Medium))
        col.addWidget(lbl_sub); col.addWidget(lbl_title)

        sw_col = QVBoxLayout()
        sw_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        lbl_sw = QLabel("Oscuro"); lbl_sw.setFont(Fonts.get(10))
        lbl_sw.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl_sw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.switch = ToggleSwitch(on_toggle=self._on_mode_toggle)
        sw_col.addWidget(lbl_sw); sw_col.addWidget(self.switch)

        top.addLayout(col); top.addStretch(); top.addLayout(sw_col)
        root.addLayout(top)

        # ── Scroll area ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setSpacing(10)
        c_lay.setContentsMargins(0, 0, 0, 0)

        # Avatar + nombre + edad + teléfono
        top_card = QWidget(); top_card.setObjectName("field_card")
        top_card_lay = QHBoxLayout(top_card)
        top_card_lay.setContentsMargins(16, 16, 16, 16)
        top_card_lay.setSpacing(16)

        # Avatar
        avatar_col = QVBoxLayout()
        avatar_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar = AvatarWidget()
        btn_photo = QPushButton("Cambiar foto")
        btn_photo.setFont(Fonts.get(9))
        btn_photo.setFixedHeight(28)
        btn_photo.clicked.connect(self._pick_photo)
        btn_photo.setStyleSheet(
            f"background:{Colors.SLATE_100}; color:{Colors.SLATE_600};"
            "border-radius:6px; border:none;"
        )
        avatar_col.addWidget(self.avatar)
        avatar_col.addSpacing(6)
        avatar_col.addWidget(btn_photo)
        top_card_lay.addLayout(avatar_col)

        # Campos básicos
        fields_col = QVBoxLayout(); fields_col.setSpacing(8)
        self.f_name  = self._inline_field("Nombre completo", "Ej. María García López")
        self.f_age   = self._inline_field("Edad", "Ej. 45")
        self.f_phone = self._inline_field("Teléfono", "Ej. +52 55 1234 5678")
        fields_col.addWidget(self.f_name)
        fields_col.addWidget(self.f_age)
        fields_col.addWidget(self.f_phone)
        top_card_lay.addLayout(fields_col, stretch=1)
        c_lay.addWidget(top_card)
        self._shadow_widgets.append(top_card)

        # Condiciones crónicas
        self.f_conditions = FieldCard(
            "Condiciones crónicas",
            "Ej. Diabetes tipo 2, Hipertensión...",
            multiline=True
        )
        c_lay.addWidget(self.f_conditions)
        self._shadow_widgets.append(self.f_conditions)

        # Medicamentos
        self.f_medications = FieldCard(
            "Medicamentos actuales",
            "Ej. Metformina 850mg, Losartán 50mg...",
            multiline=True
        )
        c_lay.addWidget(self.f_medications)
        self._shadow_widgets.append(self.f_medications)

        # Alergias
        self.f_allergies = FieldCard(
            "Alergias conocidas",
            "Ej. Penicilina, AINEs...",
            multiline=True
        )
        c_lay.addWidget(self.f_allergies)
        self._shadow_widgets.append(self.f_allergies)

        # Notas médicas
        self.f_notes = FieldCard(
            "Notas médicas",
            "Observaciones adicionales...",
            multiline=True
        )
        c_lay.addWidget(self.f_notes)
        self._shadow_widgets.append(self.f_notes)

        c_lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # ── Botones: Cerrar Sesión + Guardar ─────────────────
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        
        # Botón cerrar sesión
        self.btn_close_session = QPushButton("🔒  Cerrar Sesión")
        self.btn_close_session.setFont(Fonts.get(13, QFont.Weight.Medium))
        self.btn_close_session.setFixedHeight(44)
        self.btn_close_session.clicked.connect(self._close_session)
        self.btn_close_session.setStyleSheet(
            f"background:{Colors.CORAL_600}; color:#fff; border-radius:10px; border:none;"
        )
        
        # Botón guardar
        self.btn_save = QPushButton("💾  Guardar datos del paciente")
        self.btn_save.setFont(Fonts.get(13, QFont.Weight.Medium))
        self.btn_save.setFixedHeight(44)
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setStyleSheet(
            f"background:{Colors.TEAL_500}; color:#fff; border-radius:10px; border:none;"
        )
        
        buttons_row.addWidget(self.btn_close_session)
        buttons_row.addWidget(self.btn_save)
        root.addLayout(buttons_row)
        
        self._refresh_shadows()

    def _inline_field(self, label: str, placeholder: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lbl = QLabel(label)
        lbl.setFont(Fonts.get(10))
        lbl.setStyleSheet(f"color:{Colors.SLATE_400};")
        lbl.setFixedWidth(120)
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFont(Fonts.get(13))
        inp.setStyleSheet(
            f"background:{Colors.SLATE_50}; border:0.5px solid {Colors.SLATE_200};"
            "border-radius:8px; padding:4px 10px; color:inherit;"
        )
        inp.setFixedHeight(32)
        lay.addWidget(lbl)
        lay.addWidget(inp)
        w._input = inp
        return w

    def _pick_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar foto", "",
            "Imagenes (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._photo_path = path
            self.avatar.set_photo(path)

    def _load_into_fields(self):
        d = self._data
        self.f_name._input.setText(d.get("name", ""))
        self.f_age._input.setText(d.get("age", ""))
        self.f_phone._input.setText(d.get("phone", ""))
        self.f_conditions.set_value(d.get("conditions", ""))
        self.f_medications.set_value(d.get("medications", ""))
        self.f_allergies.set_value(d.get("allergies", ""))
        self.f_notes.set_value(d.get("notes", ""))
        self.avatar.set_photo(d.get("photo", ""))
        self.avatar.set_initials(d.get("name", "?"))

    def _save(self):
        name = self.f_name._input.text()
        data = {
            "name":       name,
            "age":        self.f_age._input.text(),
            "phone":      self.f_phone._input.text(),
            "conditions": self.f_conditions.value(),
            "medications":self.f_medications.value(),
            "allergies":  self.f_allergies.value(),
            "notes":      self.f_notes.value(),
            "photo":      self._photo_path,
        }
        _save_patient(data)
        self._data = data
        self.avatar.set_initials(name)
        self.btn_save.setText("✓  Guardado")
        QTimer = __import__("PyQt6.QtCore", fromlist=["QTimer"]).QTimer
        QTimer.singleShot(2000, lambda: self.btn_save.setText("💾  Guardar datos del paciente"))

    def _close_session(self):
        """Cerrar sesión actual"""
        import storage
        if storage.session_manager and storage.session_manager.has_session():
            storage.session_manager.end_session()
            self.btn_close_session.setText("✓  Sesión Cerrada")
            # Toast si el padre tiene el método
            if hasattr(self.parent(), 'toast'):
                self.parent().toast("✓ Sesión cerrada exitosamente", 3000, Colors.BLUE_400)
            # Restaurar texto del botón después de 2s
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.btn_close_session.setText("🔒  Cerrar Sesión"))
        else:
            if hasattr(self.parent(), 'toast'):
                self.parent().toast("⚠ No hay sesión activa", 2000, Colors.YELLOW_400)


    def _refresh_shadows(self):
        for w in self._shadow_widgets:
            w.setGraphicsEffect(_make_shadow(radius=16, opacity=0.09, dy=3, dark=self.dark))

    def _apply_style(self):
        bg     = Colors.DARK_BG      if self.dark else Colors.LIGHT_BG
        surf   = Colors.DARK_SURFACE if self.dark else Colors.LIGHT_SURFACE
        border = Colors.DARK_BORDER  if self.dark else Colors.LIGHT_BORDER
        text   = Colors.DARK_TEXT    if self.dark else Colors.LIGHT_TEXT
        self.setStyleSheet(f"""
            PatientWidget {{ background:{bg}; }}
            #field_card {{
                background:{surf}; border:0.5px solid {border};
                border-radius:14px;
            }}
            QLabel {{ color:{text}; background:transparent; }}
            QLineEdit, QTextEdit {{
                color:{text}; background:transparent;
            }}
            QPushButton#save_btn {{
                background:{Colors.TEAL_500}; color:#fff;
                border-radius:10px; border:none;
            }}
        """)
        self.btn_save.setStyleSheet(
            f"background:{Colors.TEAL_500}; color:#fff; border-radius:10px; border:none;"
        )
        self._refresh_shadows()

    def _on_mode_toggle(self, dark):
        self.dark = dark
        self._apply_style()
        if self.parent() and hasattr(self.parent(), "set_dark"):
            self.parent().set_dark(dark)

    def set_dark(self, dark):
        self.dark = dark
        self.switch.setChecked(dark)
        self._apply_style()
