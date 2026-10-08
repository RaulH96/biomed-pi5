#!/bin/bash
# =============================================================
#  recover_venv.sh  –  Recuperación del venv biomed-pi5
#  Raspberry Pi 5  |  Genera: <proyecto>/.venv
#  USO: cd /home/harlink/biomed-pi5 && bash recover_venv.sh
# =============================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
LOG_FILE="$PROJECT_DIR/venv_recovery.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERR ]${NC}  $*" | tee -a "$LOG_FILE"; }

# Paquetes de apt que necesita el venv:
#  · python3-lgpio: lgpio no se instala bien con pip (compila contra liblgpio)
#  · libqt6* / libxcb-cursor0: librerías gráficas que usa el wheel de PyQt6
#  · *-dev: para compilar paquetes nativos (sysv_ipc, rpi_ws281x…)
APT_PACKAGES=(
    python3-venv python3-pip python3-dev python3-full
    python3-lgpio
    libgpiod-dev libi2c-dev i2c-tools
    libusb-1.0-0-dev libftdi1-dev
    libqt6core6t64 libqt6gui6 libqt6widgets6 libxcb-cursor0
    libopenblas-dev
    libjpeg-dev libpng-dev zlib1g-dev libfreetype-dev
)

echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║   biomed-pi5  –  Recuperación de venv        ║"
echo "║   Raspberry Pi 5  ·  $(date '+%Y-%m-%d %H:%M')       ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
echo "=== Recuperación iniciada: $(date) ===" > "$LOG_FILE"

# ── 1. Python ─────────────────────────────────────────────
echo -e "\n${BOLD}${CYAN}1/5  Verificando Python 3${NC}"
if ! command -v python3 &>/dev/null; then
    error "python3 no encontrado. Instálalo primero."
    exit 1
fi
ok "$(python3 --version)"

# ── 2. requirements.txt ───────────────────────────────────
echo -e "\n${BOLD}${CYAN}2/5  Verificando requirements.txt${NC}"
if [ ! -f "$REQUIREMENTS" ]; then
    error "No se encontró $REQUIREMENTS — clona el repo completo primero."
    exit 1
fi
REQ_COUNT=$(grep -cvE '^\s*(#|$)' "$REQUIREMENTS" || true)
ok "requirements.txt encontrado ($REQ_COUNT paquetes)"

# ── 3. Dependencias del sistema ───────────────────────────
echo -e "\n${BOLD}${CYAN}3/5  Dependencias del sistema${NC}"
MISSING=()
for p in "${APT_PACKAGES[@]}"; do
    dpkg -s "$p" &>/dev/null || MISSING+=("$p")
done
if [ ${#MISSING[@]} -eq 0 ]; then
    ok "Todas las dependencias del sistema ya están instaladas"
else
    info "Faltan: ${MISSING[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends "${MISSING[@]}" 2>&1 | tee -a "$LOG_FILE"
    ok "Dependencias del sistema listas"
fi

# ── 4. Recrear venv ───────────────────────────────────────
echo -e "\n${BOLD}${CYAN}4/5  Recreando entorno virtual${NC}"
if [ -d "$VENV_DIR" ]; then
    warn "Eliminando venv anterior..."
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR" --system-site-packages
ok "Nuevo venv creado: $VENV_DIR"

source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"
ok "pip/setuptools/wheel actualizados"

info "Instalando requirements.txt..."
pip install -r "$REQUIREMENTS" 2>&1 | tee -a "$LOG_FILE"
ok "Todos los paquetes instalados"

# ── 5. Verificación ───────────────────────────────────────
echo -e "\n${BOLD}${CYAN}5/5  Verificando importaciones críticas${NC}"
FAILED=()
check() {
    if "$VENV_DIR/bin/python" -c "import $1" 2>/dev/null; then
        ok "  import $1 ✓"
    else
        warn "  import $1 ✗"
        FAILED+=("$1")
    fi
}

check PyQt6.QtWidgets
check matplotlib.backends.backend_qtagg
check numpy
check scipy.signal
check yaml
check lgpio
check smbus2
check board
check adafruit_ads1x15.ads1115
check adafruit_mlx90640
check paho.mqtt.client
check fastapi
check uvicorn

echo ""
if [ ${#FAILED[@]} -eq 0 ]; then
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║          Recuperación completada ✓           ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
else
    echo -e "${BOLD}${RED}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${RED}║     Recuperación con ${#FAILED[@]} import(s) fallido(s)     ║${NC}"
    echo -e "${BOLD}${RED}╚══════════════════════════════════════════════╝${NC}"
    for p in "${FAILED[@]}"; do echo -e "  ${RED}·${NC} $p"; done
    echo -e "  Diagnóstico: ${CYAN}$VENV_DIR/bin/python -c 'import <modulo>'${NC}"
fi

echo ""
info "Activar venv: source $VENV_DIR/bin/activate"
info "Log: $LOG_FILE"
echo "=== Finalizado: $(date) ===" >> "$LOG_FILE"

[ ${#FAILED[@]} -eq 0 ]
