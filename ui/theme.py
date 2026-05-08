#/home/harlink/biomed-pi5/ui/theme.py

from PyQt6.QtGui import QColor, QFont

# ── Paleta de colores ─────────────────────────────────────────
class Colors:
    # Teal — temperatura
    TEAL_50  = "#E8F6F3"
    TEAL_300 = "#5BB8A0"
    TEAL_500 = "#2A9080"
    TEAL_700 = "#1A6560"

    # Blue — SpO2
    BLUE_100 = "#DFF0FB"
    BLUE_400 = "#4AAADE"
    BLUE_600 = "#1E72A8"

    # Coral — pulso
    CORAL_100 = "#FDDDD6"
    CORAL_400 = "#E8845A"
    CORAL_600 = "#C05A38"

    # Amber — presión
    AMBER_100 = "#FFF0D6"
    AMBER_400 = "#F0A830"
    AMBER_600 = "#C07A10"

    # Green — estado normal
    GREEN_100 = "#DFF5E8"
    GREEN_400 = "#45C07A"
    GREEN_600 = "#1E8A50"

    # Slate — neutros
    SLATE_50  = "#F4F5F7"
    SLATE_100 = "#E4E6EB"
    SLATE_200 = "#CDD0D8"
    SLATE_400 = "#8B90A0"
    SLATE_600 = "#555A6A"
    SLATE_800 = "#2E3240"
    SLATE_900 = "#1C1F2B"

    # Superficies modo claro
    LIGHT_BG        = "#F7F8FA"
    LIGHT_SURFACE   = "#FFFFFF"
    LIGHT_BORDER    = "#CDD0D8"
    LIGHT_TEXT      = "#2E3240"
    LIGHT_TEXT_MUTED= "#8B90A0"

    # Superficies modo oscuro
    DARK_BG         = "#1C1F2B"
    DARK_SURFACE    = "#2E3240"
    DARK_BORDER     = "#3A3F52"
    DARK_TEXT       = "#E4E6EB"
    DARK_TEXT_MUTED = "#8B90A0"

    # Semántica clínica
    STATE_NORMAL     = ("#DFF5E8", "#1E8A50")   # (fondo, texto)
    STATE_FEBRICULA  = ("#FFF0D6", "#C07A10")
    STATE_FIEBRE     = ("#FDDDD6", "#C05A38")
    STATE_HIPOTERMIA = ("#DFF0FB", "#1E72A8")
    STATE_UNKNOWN    = ("#E4E6EB", "#555A6A")

    # Color por sensor
    SENSOR_TEMP     = TEAL_500
    SENSOR_SPO2     = BLUE_400
    SENSOR_PULSE    = CORAL_400
    SENSOR_PRESSURE = AMBER_400


# ── Tipografía ────────────────────────────────────────────────
class Fonts:
    TITLE   = ("Inter", 22, QFont.Weight.Medium)
    SECTION = ("Inter", 17, QFont.Weight.Medium)
    LABEL   = ("Inter", 14, QFont.Weight.Medium)
    BODY    = ("Inter", 15, QFont.Weight.Normal)
    CAPTION = ("Inter", 11, QFont.Weight.Normal)
    DATA_XL = ("Inter", 36, QFont.Weight.Medium)  # número principal
    DATA_LG = ("Inter", 28, QFont.Weight.Medium)
    DATA_MD = ("Inter", 20, QFont.Weight.Medium)

    @staticmethod
    def get(size: int, weight=QFont.Weight.Normal) -> QFont:
        f = QFont("Inter")
        f.setPixelSize(size)
        f.setWeight(weight)
        return f


# ── Hojas de estilo QSS ───────────────────────────────────────
def get_stylesheet(dark: bool = False) -> str:
    if dark:
        bg        = Colors.DARK_BG
        surface   = Colors.DARK_SURFACE
        border    = Colors.DARK_BORDER
        text      = Colors.DARK_TEXT
        text_muted= Colors.DARK_TEXT_MUTED
    else:
        bg        = Colors.LIGHT_BG
        surface   = Colors.LIGHT_SURFACE
        border    = Colors.LIGHT_BORDER
        text      = Colors.LIGHT_TEXT
        text_muted= Colors.LIGHT_TEXT_MUTED

    return f"""
    QMainWindow, QWidget#root {{
        background-color: {bg};
    }}
    QWidget#surface {{
        background-color: {surface};
        border: 0.5px solid {border};
        border-radius: 14px;
    }}
    QLabel {{
        color: {text};
        background: transparent;
    }}
    QLabel#muted {{
        color: {text_muted};
    }}
    QLabel#data_xl {{
        color: {Colors.TEAL_500};
        font-size: 36px;
        font-weight: 500;
    }}
    QPushButton#toggle_mode {{
        background: transparent;
        border: 0.5px solid {border};
        border-radius: 8px;
        color: {text_muted};
        padding: 6px 14px;
        font-size: 12px;
    }}
    QPushButton#toggle_mode:hover {{
        background: {surface};
    }}
    QScrollBar:vertical {{
        width: 6px;
        background: transparent;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        border-radius: 3px;
    }}
    """


# ── Helper: badge de estado clínico ──────────────────────────
def state_badge_style(state: str, dark: bool = False) -> tuple[str, str]:
    """
    Retorna (bg_color, text_color) según el estado clínico.
    Usar con QLabel para pintar el badge.
    """
    MAP = {
        "normal":          Colors.STATE_NORMAL,
        "normal_baja":     Colors.STATE_NORMAL,
        "febricula":       Colors.STATE_FEBRICULA,
        "fiebre_moderada": Colors.STATE_FIEBRE,
        "fiebre_alta":     Colors.STATE_FIEBRE,
        "fiebre_muy_alta": Colors.STATE_FIEBRE,
        "hipotermia":      Colors.STATE_HIPOTERMIA,
    }
    bg, fg = MAP.get(state, Colors.STATE_UNKNOWN)
    # en modo oscuro oscurecer el fondo del badge
    if dark:
        bg = bg.replace("DF", "1A").replace("FF", "2A")
    return bg, fg