#!/bin/bash
# =============================================================
#  setup.sh  –  Setup completo biomed-pi5 desde cero
#
#  Ejecutar justo después de: git clone https://github.com/RaulH96/biomed-pi5
#  USO: cd biomed-pi5 && bash setup.sh
#
#  Instala y configura TODO:
#    · Python venv + dependencias
#    · Mosquitto MQTT broker
#    · Node.js + npm + dependencias webapp
#    · I2C, SPI habilitados
#    · Hostname harlink → harlink.local (sin depender de IP)
#    · avahi-daemon para mDNS
#    · Directorio assets/
#    · PWA compilada para producción
#    · Servicios de usuario + arranque automático (todo arranca al encender)
# =============================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_FILE="$PROJECT_DIR/setup.log"
RUN_USER="$(id -un)"
NEED_REBOOT=0

# Los servicios se instalan para el usuario que corre el script: con sudo
# quedarían a nombre de root y la Edge UI no podría abrirse en el escritorio.
if [ "$(id -u)" -eq 0 ]; then
    echo "No ejecutes setup.sh con sudo: corre 'bash setup.sh' (pedirá la contraseña cuando haga falta)."
    exit 1
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERR ]${NC}  $*" | tee -a "$LOG_FILE"; exit 1; }
step()  { echo -e "\n${BOLD}${CYAN}$*${NC}"; }

echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║        biomed-pi5  –  Setup desde cero               ║"
echo "║        Raspberry Pi 5  ·  $(date '+%Y-%m-%d %H:%M')         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "=== Setup iniciado: $(date) ===" > "$LOG_FILE"

# Verificar que estamos en el directorio correcto
if [ ! -f "$PROJECT_DIR/main.py" ] || [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    error "Ejecuta este script desde el directorio raíz del proyecto biomed-pi5"
fi

# ─────────────────────────────────────────────────────────────
# 1. Sistema: actualizar e instalar paquetes base
# ─────────────────────────────────────────────────────────────
step "1/9  Paquetes del sistema"
# python3-lgpio: lgpio no se instala bien con pip (compila contra liblgpio)
# libqt6* / libxcb-cursor0: librerías gráficas que usa el wheel de PyQt6
APT_PACKAGES=(
    python3-venv python3-pip python3-dev python3-full
    python3-lgpio
    libgpiod-dev libi2c-dev i2c-tools
    libusb-1.0-0-dev libftdi1-dev
    libqt6core6t64 libqt6gui6 libqt6widgets6 libxcb-cursor0
    libopenblas-dev
    libjpeg-dev libpng-dev zlib1g-dev libfreetype-dev
    git curl wget openssl sqlite3 tmux lxterminal
)
MISSING=()
for p in "${APT_PACKAGES[@]}"; do
    dpkg -s "$p" &>/dev/null || MISSING+=("$p")
done
if [ ${#MISSING[@]} -eq 0 ]; then
    ok "Paquetes base ya instalados"
else
    info "Instalando: ${MISSING[*]}"
    sudo apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
    sudo apt-get install -y --fix-missing "${MISSING[@]}" 2>&1 | tee -a "$LOG_FILE"
    ok "Paquetes base instalados"
fi

# ─────────────────────────────────────────────────────────────
# 2. Mosquitto MQTT Broker
# ─────────────────────────────────────────────────────────────
step "2/9  Mosquitto MQTT Broker"
# mosquitto vive en /usr/sbin (fuera del PATH de usuario): se consulta a dpkg.
# Ojo: "mosquitto -v" no imprime la versión, ARRANCA el broker en modo verbose.
if dpkg -s mosquitto &>/dev/null; then
    ok "Mosquitto ya instalado: $(dpkg-query -W -f='${Version}' mosquitto)"
else
    info "Instalando Mosquitto..."
    sudo apt-get install -y mosquitto mosquitto-clients 2>&1 | tee -a "$LOG_FILE"
    ok "Mosquitto instalado"
fi

systemctl is-enabled --quiet mosquitto || sudo systemctl enable mosquitto
systemctl is-active  --quiet mosquitto || sudo systemctl start mosquitto
ok "Mosquitto activo y habilitado en arranque"

# ─────────────────────────────────────────────────────────────
# 3. Node.js + npm
# ─────────────────────────────────────────────────────────────
step "3/9  Node.js + npm"
if command -v node &>/dev/null; then
    ok "Node.js ya instalado: $(node --version)"
else
    info "Instalando Node.js..."
    sudo apt-get update -qq
    sudo apt-get install -y --fix-missing nodejs npm 2>&1 | tee -a "$LOG_FILE"
    ok "Node.js $(node --version) instalado"
fi

# ─────────────────────────────────────────────────────────────
# 4. Interfaces de hardware: I2C + SPI
# ─────────────────────────────────────────────────────────────
step "4/9  Interfaces de hardware (I2C / SPI)"
if [ -e /dev/i2c-1 ] && [ -e /dev/spidev0.0 ]; then
    ok "I2C y SPI ya habilitados"
elif command -v raspi-config &>/dev/null; then
    sudo raspi-config nonint do_i2c 0 && ok "I2C habilitado"
    sudo raspi-config nonint do_spi 0 && ok "SPI habilitado"
    NEED_REBOOT=1
else
    warn "raspi-config no disponible — habilita I2C/SPI manualmente"
fi

# ─────────────────────────────────────────────────────────────
# 5. Hostname harlink + avahi (harlink.local sin depender de IP)
# ─────────────────────────────────────────────────────────────
step "5/9  Hostname y mDNS (harlink.local)"
CURRENT_HOSTNAME=$(hostname)
if [ "$CURRENT_HOSTNAME" != "Harlink" ] && [ "$CURRENT_HOSTNAME" != "harlink" ]; then
    info "Configurando hostname → harlink"
    sudo hostnamectl set-hostname harlink
    sudo sed -i "s/$CURRENT_HOSTNAME/harlink/g" /etc/hosts
    ok "Hostname configurado: harlink"
    NEED_REBOOT=1
else
    ok "Hostname ya correcto: $CURRENT_HOSTNAME"
fi

# avahi-daemon para resolver harlink.local en la red
if ! dpkg -s avahi-daemon &>/dev/null; then
    info "Instalando avahi-daemon..."
    sudo apt-get install -y avahi-daemon 2>&1 | tee -a "$LOG_FILE"
fi
systemctl is-enabled --quiet avahi-daemon || sudo systemctl enable avahi-daemon
systemctl is-active  --quiet avahi-daemon || sudo systemctl start avahi-daemon
ok "avahi-daemon activo → accesible como harlink.local desde cualquier dispositivo en red"

# ─────────────────────────────────────────────────────────────
# 6. Python venv + requirements
# ─────────────────────────────────────────────────────────────
step "6/9  Python venv + dependencias"
if [ -d "$VENV_DIR" ]; then
    warn "Eliminando venv anterior..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR" --system-site-packages
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"

# requirements.lock fija también las dependencias transitivas a las versiones
# verificadas. Si una ya no instala (p. ej. un Python más nuevo sin wheel),
# se reintenta sin el lock y se avisa.
LOCK="$PROJECT_DIR/requirements.lock"
if [ -f "$LOCK" ] && pip install -r "$PROJECT_DIR/requirements.txt" -c "$LOCK" 2>&1 | tee -a "$LOG_FILE"; then
    ok "Python venv listo (versiones exactas de requirements.lock)"
else
    [ -f "$LOCK" ] && warn "Falló con requirements.lock — reintentando con versiones libres"
    pip install -r "$PROJECT_DIR/requirements.txt" 2>&1 | tee -a "$LOG_FILE"
    ok "Python venv listo (sin lock: revisa que la app funcione y regenera el lock)"
fi

# ─────────────────────────────────────────────────────────────
# 7. Webapp Next.js: instalar node_modules + certificados SSL
# ─────────────────────────────────────────────────────────────
step "7/9  Webapp Next.js (npm ci + SSL + compilación)"
WEBAPP_DIR="$PROJECT_DIR/services/webapp"
if [ -f "$WEBAPP_DIR/package.json" ]; then
    info "Instalando dependencias npm..."
    cd "$WEBAPP_DIR"
    # npm ci instala exactamente lo que fija package-lock.json (reproducible);
    # npm install solo si el lock no existe o no cuadra con package.json.
    if [ -f package-lock.json ] && npm ci 2>&1 | tee -a "$LOG_FILE"; then
        :
    else
        warn "npm ci no aplicable — usando npm install"
        npm install 2>&1 | tee -a "$LOG_FILE"
    fi
    cd "$PROJECT_DIR"
    ok "node_modules instalados"
else
    warn "No se encontró $WEBAPP_DIR/package.json"
fi

# Certificados SSL para modo producción HTTPS
# Los .pem están gitignoreados — se regeneran en cada instalación
if [ ! -f "$WEBAPP_DIR/harlink.local.pem" ]; then
    if command -v openssl &>/dev/null; then
        info "Generando certificado SSL autofirmado para harlink.local..."
        openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
            -keyout "$WEBAPP_DIR/harlink.local-key.pem" \
            -out    "$WEBAPP_DIR/harlink.local.pem" \
            -subj   "/CN=harlink.local" \
            -addext "subjectAltName=DNS:harlink.local,DNS:localhost,IP:127.0.0.1" \
            2>&1 | tee -a "$LOG_FILE"
        ok "Certificado SSL generado (válido 10 años)"
    else
        warn "openssl no encontrado — instálalo para modo HTTPS producción: sudo apt install openssl"
    fi
else
    ok "Certificado SSL ya existe"
fi

# Compilación de producción: la PWA de producción corre con NODE_ENV=production
# (más rápida, menos RAM, sin el overlay de errores de desarrollo).
if [ -f "$WEBAPP_DIR/package.json" ]; then
    info "Compilando PWA para producción (npm run build)..."
    cd "$WEBAPP_DIR"
    if npm run build 2>&1 | tee -a "$LOG_FILE"; then
        ok "PWA compilada"
    else
        warn "Falló npm run build — revisa setup.log (biomed-control.sh build para reintentar)"
    fi
    cd "$PROJECT_DIR"
fi

# ─────────────────────────────────────────────────────────────
# 8. Directorios, estructura y accesos directos del escritorio
# ─────────────────────────────────────────────────────────────
step "8/9  Estructura del proyecto + accesos directos"
mkdir -p "$PROJECT_DIR/assets"
mkdir -p "$PROJECT_DIR/data"
ok "Directorios assets/ y data/ verificados"

# Los accesos directos exigen que su Exec sea ejecutable: si no, el escritorio
# los rechaza con "Archivo de entrada de escritorio no válido".
chmod +x "$PROJECT_DIR"/*.sh
ok "Scripts .sh marcados como ejecutables"

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/Biomed-Pi5.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Biomed Pi5 (DESARROLLO)
Comment=Sistema de Monitoreo Biomédico - Modo Desarrollo (Hot Reload)
Exec=$PROJECT_DIR/start_biomed.sh
Icon=$PROJECT_DIR/icon.png
Terminal=false
Categories=Science;MedicalSoftware;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/Biomed-Pi5.desktop"

cat > "$DESKTOP_DIR/Biomed-Pi5-PROD.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Biomed Pi5 (PRODUCCIÓN)
Comment=Sistema de Monitoreo Biomédico - Modo Producción (PWA Instalable)
Exec=$PROJECT_DIR/start_biomed_prod.sh
Icon=$PROJECT_DIR/icon.png
Terminal=false
Categories=Science;MedicalSoftware;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/Biomed-Pi5-PROD.desktop"

ok "Accesos directos creados en el escritorio"

# ─────────────────────────────────────────────────────────────
# 9. Servicios y arranque automático
# ─────────────────────────────────────────────────────────────
step "9/9  Servicios y arranque automático"
CONTROL="$PROJECT_DIR/biomed-control.sh"
strip_colors() { sed 's/\x1b\[[0-9;]*m//g'; }

# Versiones anteriores instalaban servicios de SISTEMA (/etc/systemd/system):
# chocarían en los puertos con los nuevos servicios de usuario.
LEGACY_UNITS=$(ls /etc/systemd/system/biomed-*.service 2>/dev/null || true)
if [ -n "$LEGACY_UNITS" ]; then
    info "Retirando servicios de sistema antiguos..."
    for unit in $LEGACY_UNITS; do
        sudo systemctl disable --now "$(basename "$unit")" 2>&1 | tee -a "$LOG_FILE" || true
        sudo rm -f "$unit"
    done
    sudo systemctl daemon-reload
    ok "Servicios de sistema antiguos retirados"
fi

# Linger: el gestor de servicios del usuario arranca al encender la Pi,
# sin esperar a que alguien inicie sesión.
if [ "$(loginctl show-user "$RUN_USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
    sudo loginctl enable-linger "$RUN_USER"
fi
ok "Linger activo para $RUN_USER"

"$CONTROL" install
ok "Servicios de usuario instalados (~/.config/systemd/user)"
"$CONTROL" enable  2>&1 | strip_colors | grep -E '▸|⚠' | tee -a "$LOG_FILE" || true
ok "Arranque automático habilitado (servicios + Edge UI en el escritorio)"
"$CONTROL" restart 2>&1 | strip_colors | grep -E '▸|PWA' | tee -a "$LOG_FILE" || true

# ─────────────────────────────────────────────────────────────
# Verificación final
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}══════════════  Verificación final  ══════════════${NC}"

ERRORS=0
check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "  $1 ✓  ($(${1} --version 2>&1 | head -1))"
    else
        warn "  $1 ✗  NO encontrado"
        ERRORS=$((ERRORS+1))
    fi
}
check_svc() {
    if systemctl is-active --quiet "$1"; then
        ok "  servicio $1 ✓  activo"
    else
        warn "  servicio $1 ✗  no activo"
        ERRORS=$((ERRORS+1))
    fi
}
check_py() {
    if "$VENV_DIR/bin/python" -c "import $1" 2>/dev/null; then
        ok "  python: import $1 ✓"
    else
        warn "  python: import $1 ✗"
        ERRORS=$((ERRORS+1))
    fi
}

check_cmd python3
check_cmd node
check_cmd npm
check_svc mosquitto
check_svc avahi-daemon
check_py PyQt6.QtWidgets
check_py matplotlib.backends.backend_qtagg
check_py numpy
check_py scipy.signal
check_py yaml
check_py lgpio
check_py smbus2
check_py board
check_py adafruit_ads1x15.ads1115
check_py adafruit_mlx90640
check_py paho.mqtt.client
check_py fastapi
check_py uvicorn

check_user_svc() {
    if systemctl --user is-active --quiet "$1"; then
        ok "  servicio $1 ✓  activo (arranque automático: $(systemctl --user is-enabled "$1" 2>/dev/null))"
    else
        warn "  servicio $1 ✗  no activo (ver: ./biomed-control.sh logs ${1#biomed-})"
        ERRORS=$((ERRORS+1))
    fi
}
check_user_svc biomed-mqtt-subscriber
check_user_svc biomed-fastapi
check_user_svc biomed-pwa

# Prueba de punta a punta: página HTTPS + API a través del proxy /backend
PWA_OK=0
for _ in $(seq 1 30); do
    if curl -sk --max-time 5 https://localhost:3000/backend/health 2>/dev/null | grep -q '"ok"'; then
        PWA_OK=1; break
    fi
    sleep 2
done
if [ $PWA_OK -eq 1 ]; then
    ok "  PWA + API responden ✓  (https://localhost:3000/backend/health)"
else
    warn "  PWA/API no responden en https://localhost:3000 ✗"
    ERRORS=$((ERRORS+1))
fi
if [ -f "$HOME/.config/autostart/biomed-edge.desktop" ]; then
    ok "  Edge UI ✓  se abre sola al iniciar el escritorio"
else
    warn "  Edge UI ✗  sin autoarranque"
    ERRORS=$((ERRORS+1))
fi

# ─────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────
echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║          ✓  Setup completado sin errores              ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${BOLD}${YELLOW}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${YELLOW}║    Setup completado con $ERRORS advertencia(s)              ║${NC}"
    echo -e "${BOLD}${YELLOW}╚══════════════════════════════════════════════════════╝${NC}"
fi

IP_ACTUAL="$(hostname -I | awk '{print $1}')"
echo ""
echo -e "${BOLD}Todo arranca solo al encender la Pi:${NC}"
echo -e "  PWA (celular)    →  ${CYAN}https://harlink.local:3000${NC}   ó   ${CYAN}https://$IP_ACTUAL:3000${NC}"
echo -e "  FastAPI docs     →  ${CYAN}http://harlink.local:8000/docs${NC}"
echo -e "  Edge UI (PyQt6)  →  se abre sola en el escritorio"
echo ""
echo -e "${BOLD}Control:${NC} ./biomed-control.sh   (status · restart · logs · disable para programar)"
echo -e "${BOLD}Desarrollo:${NC} ícono 'Biomed Pi5 (DESARROLLO)' (detiene los servicios y abre hot reload)"
echo ""
if [ $NEED_REBOOT -eq 1 ]; then
    echo -e "${YELLOW}⚠  Se requiere reinicio para activar I2C/SPI / el nuevo hostname${NC}"
    echo ""
    # Sin terminal (ssh no interactivo, cron…) read devuelve error y set -e
    # cortaría el script: se toma como "no".
    read -p "¿Reiniciar ahora? (s/N): " REBOOT || REBOOT=""
    if [[ "$REBOOT" =~ ^[Ss]$ ]]; then
        echo "=== Setup finalizado: $(date) ===" >> "$LOG_FILE"
        info "Reiniciando..."
        sudo reboot
    fi
else
    ok "No hace falta reiniciar: todo está corriendo"
fi

echo "=== Setup finalizado: $(date) ===" >> "$LOG_FILE"
