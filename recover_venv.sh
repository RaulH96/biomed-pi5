#!/bin/bash
# =============================================================
#  recover_venv.sh  –  Recuperación del venv biomed-pi5
#  Raspberry Pi 5  |  Genera: /home/harlink/biomed-pi5/.venv
#  USO: cd /home/harlink/biomed-pi5 && bash recover_venv.sh
# =============================================================

set -euo pipefail

PROJECT_DIR="/home/harlink/biomed-pi5"
VENV_DIR="$PROJECT_DIR/.venv"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
LOG_FILE="$PROJECT_DIR/venv_recovery.log"

# ── Colores ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }

# ── Banner ─────────────────────────────────────────────────
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║   biomed-pi5  –  Recuperación de venv        ║"
echo "║   Raspberry Pi 5  ·  $(date '+%Y-%m-%d %H:%M')       ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

echo "=== Recuperación iniciada: $(date) ===" > "$LOG_FILE"

# ── 1. Verificar Python ────────────────────────────────────
echo -e "\n${BOLD}${CYAN}1/6  Verificando Python 3${NC}"
if ! command -v python3 &>/dev/null; then
    error "python3 no encontrado."
    exit 1
fi
PYVER=$(python3 --version)
ok "Encontrado: $PYVER"

# ── 2. Dependencias del sistema ────────────────────────────
echo -e "\n${BOLD}${CYAN}2/6  Instalando dependencias del sistema${NC}"
info "Instalando librerías nativas necesarias..."

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3-venv python3-pip python3-dev python3-full \
    libgpiod-dev libi2c-dev i2c-tools \
    libusb-1.0-0-dev libftdi1-dev \
    libqt6core6t64 libqt6gui6 libqt6widgets6 \
    libopenblas-dev \
    libjpeg-dev libpng-dev zlib1g-dev \
    libfreetype-dev \
    2>&1 | tee -a "$LOG_FILE"

ok "Dependencias del sistema listas"

# ── 3. Eliminar venv roto y crear uno nuevo ────────────────
echo -e "\n${BOLD}${CYAN}3/6  Recreando el entorno virtual${NC}"

if [ -d "$VENV_DIR" ]; then
    warn "Eliminando venv anterior: $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR" --system-site-packages
ok "Nuevo venv creado en $VENV_DIR"

# Activar venv
source "$VENV_DIR/bin/activate"
ok "venv activado"

# Actualizar pip/setuptools/wheel
pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"

# ── 4. Escribir requirements.txt ───────────────────────────
echo -e "\n${BOLD}${CYAN}4/6  Escribiendo requirements.txt${NC}"

cat > "$REQUIREMENTS" << 'REQS'
Adafruit-Blinka==9.1.0
adafruit-circuitpython-busdevice==5.2.17
adafruit-circuitpython-connectionmanager==3.1.8
adafruit-circuitpython-mlx90640==1.3.9
adafruit-circuitpython-register==1.11.3
adafruit-circuitpython-requests==4.1.17
adafruit-circuitpython-typing==1.12.3
Adafruit-PlatformDetect==3.88.0
Adafruit-PureIO==1.1.11
binho-host-adapter==0.1.6
colorama==0.4.6
contourpy==1.3.3
cycler==0.12.1
fonttools==4.62.1
kiwisolver==1.5.0
lgpio==0.2.2.0
matplotlib==3.10.9
numpy==2.4.4
packaging==26.2
pillow==12.2.0
pyftdi==0.57.1
pyparsing==3.3.2
PyQt6==6.11.0
PyQt6-Qt6==6.11.0
PyQt6_sip==13.11.1
pyqtgraph==0.14.0
pyserial==3.5
python-dateutil==2.9.0.post0
pyusb==1.3.1
PyYAML==6.0.3
scipy==1.17.1
six==1.17.0
smbus2==0.6.1
sysv_ipc==1.2.0
typing_extensions==4.15.0
REQS

ok "requirements.txt guardado"

# ── 5. Instalar paquetes ───────────────────────────────────
echo -e "\n${BOLD}${CYAN}5/6  Instalando paquetes (puede tardar varios minutos)${NC}"

info "Instalando paquetes pesados primero (numpy, scipy, pillow, matplotlib)..."
pip install \
    numpy==2.4.4 \
    scipy==1.17.1 \
    pillow==12.2.0 \
    matplotlib==3.10.9 \
    2>&1 | tee -a "$LOG_FILE"

info "Instalando el resto de requirements..."
pip install -r "$REQUIREMENTS" 2>&1 | tee -a "$LOG_FILE"

ok "Todos los paquetes instalados"

# ── 6. Verificación de importaciones ──────────────────────
echo -e "\n${BOLD}${CYAN}6/6  Verificando importaciones críticas${NC}"

FAILED=()
check_import() {
    local pkg=$1
    if python3 -c "import $pkg" 2>/dev/null; then
        ok "  import $pkg  ✓"
    else
        warn "  import $pkg  ✗"
        FAILED+=("$pkg")
    fi
}

check_import numpy
check_import scipy
check_import matplotlib
check_import PIL
check_import serial
check_import smbus2
check_import yaml
check_import pyqtgraph
check_import board
check_import adafruit_mlx90640

# ── Resumen ────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║            Recuperación completada           ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"

if [ ${#FAILED[@]} -gt 0 ]; then
    warn "Paquetes con advertencia (pueden requerir hardware/GPIO):"
    for p in "${FAILED[@]}"; do
        echo -e "  ${YELLOW}·${NC} $p"
    done
fi

echo ""
info "Para activar el venv en el futuro:"
echo -e "  ${CYAN}source $VENV_DIR/bin/activate${NC}"
echo ""
info "Log completo en: $LOG_FILE"
echo "=== Recuperación finalizada: $(date) ===" >> "$LOG_FILE"
