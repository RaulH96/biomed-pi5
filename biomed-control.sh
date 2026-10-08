#!/bin/bash
# Control de servicios Biomed Pi5
#
#  · Servicios de fondo → servicios systemd de USUARIO (no requieren sudo):
#      biomed-mqtt-subscriber · biomed-fastapi · biomed-pwa
#    Con "linger" activo (lo hace setup.sh) arrancan al encender la Pi,
#    aunque nadie haya iniciado sesión.
#  · Edge UI (PyQt6) → necesita el escritorio (Wayland), así que no es un
#    servicio: arranca con el autoarranque del escritorio
#    (~/.config/autostart/biomed-edge.desktop).

PROJECT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
WEBAPP_DIR="$PROJECT_DIR/services/webapp"
LOG_DIR="$PROJECT_DIR/logs"
SERVICES="biomed-mqtt-subscriber biomed-fastapi biomed-pwa"
UNIT_DIR="$HOME/.config/systemd/user"
AUTOSTART_FILE="$HOME/.config/autostart/biomed-edge.desktop"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok_mark()   { echo -e "${GREEN}✓${NC}"; }
fail_mark() { echo -e "${RED}✗${NC}"; }

show_header() {
    [ -t 1 ] && clear
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   🩺 Biomed Pi5 - Control de Servicios${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

show_menu() {
    show_header
    echo -e "${CYAN}Servicios:${NC} Edge, MQTT Subscriber, FastAPI, PWA"
    echo ""
    echo -e "${GREEN}[1]${NC} ▶  Iniciar todos los servicios"
    echo -e "${GREEN}[2]${NC} ◼  Detener todos los servicios"
    echo -e "${GREEN}[3]${NC} ⟳  Reiniciar todos los servicios"
    echo -e "${GREEN}[4]${NC} ℹ  Ver estado de servicios"
    echo ""
    echo -e "${YELLOW}[5]${NC} ✓  Habilitar inicio automático (boot)"
    echo -e "${YELLOW}[6]${NC} ✗  Deshabilitar inicio automático"
    echo -e "${YELLOW}[7]${NC} ?  Verificar configuración de arranque"
    echo ""
    echo -e "${CYAN}[8]${NC} 📋 Ver logs en tiempo real"
    echo -e "${CYAN}[9]${NC} 🔧 Reinstalar servicios"
    echo -e "${CYAN}[10]${NC} 🧹 Limpiar logs antiguos"
    echo -e "${CYAN}[11]${NC} 🏗  Recompilar PWA (tras editar la webapp)"
    echo ""
    echo -e "${RED}[0]${NC} Salir"
    echo ""
    echo -ne "${BLUE}Selecciona una opción [0-11]:${NC} "
}

# ── Edge UI (proceso de escritorio) ─────────────────────────────
edge_pids() {
    # main.py de ESTE proyecto (por ruta o por directorio de trabajo)
    local pid
    for pid in $(pgrep -f 'python[0-9.]* (.*/)?main\.py$'); do
        if tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "$PROJECT_DIR/main.py" \
           || [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$PROJECT_DIR" ]; then
            echo "$pid"
        fi
    done
}

edge_running() { [ -n "$(edge_pids)" ]; }

edge_start() {
    edge_running && return 0
    local display="${WAYLAND_DISPLAY:-}"
    if [ -z "$display" ]; then
        display=$(ls "$XDG_RUNTIME_DIR" 2>/dev/null | grep -E '^wayland-[0-9]+$' | head -1)
    fi
    [ -z "$display" ] && return 1    # no hay escritorio (p. ej. aún en el arranque)
    mkdir -p "$LOG_DIR"
    # setsid -f: lanza la Edge UI en su propia sesión y regresa de inmediato,
    # sin dejar ningún proceso intermedio reteniendo la salida de quien llamó
    # (si no, "biomed-control.sh restart | ..." en setup.sh no terminaría nunca).
    (cd "$PROJECT_DIR" && WAYLAND_DISPLAY="$display" exec setsid -f \
        "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/main.py" \
        >> "$LOG_DIR/edge.log" 2>&1 < /dev/null)
    return 0
}

edge_stop() {
    local pids
    pids=$(edge_pids)
    [ -z "$pids" ] && return 0
    kill $pids 2>/dev/null
    for _ in 1 2 3 4 5; do edge_running || return 0; sleep 1; done
    kill -9 $(edge_pids) 2>/dev/null
    return 0
}

# Procesos del modo DESARROLLO (start_biomed.sh): ocupan los puertos 8000/3000
stop_dev_processes() {
    pkill -f "uvicorn main:app .*--reload" 2>/dev/null
    pkill -f "next dev" 2>/dev/null
    pkill -f "npm run dev" 2>/dev/null
    # start-https.mjs lanzado a mano (el del servicio ya se detuvo con systemctl)
    local pid
    for pid in $(pgrep -f 'node start-https\.mjs'); do
        [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$WEBAPP_DIR" ] && kill "$pid" 2>/dev/null
    done
    # mqtt_subscriber.py lanzado a mano
    for pid in $(pgrep -f 'python[0-9.]* mqtt_subscriber\.py'); do
        [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$PROJECT_DIR/services" ] && kill "$pid" 2>/dev/null
    done
    return 0
}

# ── Servicios ───────────────────────────────────────────────────
install_services() {
    mkdir -p "$UNIT_DIR" "$LOG_DIR"
    local node_bin
    node_bin="$(command -v node || echo /usr/bin/node)"

    cat > "$UNIT_DIR/biomed-mqtt-subscriber.service" << EOF
[Unit]
Description=Biomed Pi5 - MQTT Subscriber (replica MQTT -> storage.db)

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR/services
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/.venv/bin/python mqtt_subscriber.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    cat > "$UNIT_DIR/biomed-fastapi.service" << EOF
[Unit]
Description=Biomed Pi5 - FastAPI REST API (:8000)

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR/services/storage
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    cat > "$UNIT_DIR/biomed-pwa.service" << EOF
[Unit]
Description=Biomed Pi5 - PWA producción HTTPS (:3000)
After=biomed-fastapi.service

[Service]
Type=simple
WorkingDirectory=$WEBAPP_DIR
Environment=NODE_ENV=production
ExecStart=$node_bin start-https.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
}

autostart_enable() {
    mkdir -p "$(dirname "$AUTOSTART_FILE")"
    cat > "$AUTOSTART_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Biomed Pi5 - Edge UI
Comment=Interfaz de sensores biomed-pi5 (arranque automático)
Exec=$PROJECT_DIR/biomed-control.sh edge-start
Icon=$PROJECT_DIR/icon.png
Terminal=false
EOF
}

start_services() {
    show_header
    echo -e "${BLUE}Iniciando servicios Biomed Pi5...${NC}"
    echo ""
    stop_dev_processes
    if [ ! -f "$WEBAPP_DIR/.next/BUILD_ID" ]; then
        echo -e "  ${YELLOW}PWA sin compilar — compilando (una sola vez)...${NC}"
        mkdir -p "$LOG_DIR"
        (cd "$WEBAPP_DIR" && npm run build > "$LOG_DIR/build.log" 2>&1) \
            || echo -e "  ${RED}Falló la compilación: ver $LOG_DIR/build.log${NC}"
    fi
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        systemctl --user start "$service" && ok_mark || fail_mark
    done
    echo -ne "  ▸ biomed-edge (escritorio)... "
    if edge_start; then ok_mark; else echo -e "${YELLOW}sin escritorio activo — se abrirá al iniciar sesión${NC}"; fi
    echo ""
    echo -e "${GREEN}✓ Proceso completado${NC}"
}

stop_services() {
    show_header
    echo -e "${YELLOW}Deteniendo servicios Biomed Pi5...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        systemctl --user stop "$service" && ok_mark || fail_mark
    done
    echo -ne "  ▸ biomed-edge... "
    edge_stop && ok_mark
    stop_dev_processes
    echo ""
    echo -e "${GREEN}✓ Servicios detenidos${NC}"
}

restart_services() {
    stop_services > /dev/null
    sleep 1
    start_services
}

status_services() {
    show_header
    echo -e "${BLUE}Estado de servicios:${NC}"
    echo ""
    for service in $SERVICES; do
        if systemctl --user is-active --quiet "$service"; then
            echo -e "  ${GREEN}● Activo${NC}   - $service"
        else
            echo -e "  ${RED}○ Inactivo${NC} - $service"
        fi
    done
    if edge_running; then
        echo -e "  ${GREEN}● Activo${NC}   - biomed-edge (Edge UI)"
    else
        echo -e "  ${RED}○ Inactivo${NC} - biomed-edge (Edge UI)"
    fi
    echo ""
    if curl -sk --max-time 5 https://localhost:3000/backend/health 2>/dev/null | grep -q '"ok"'; then
        echo -e "  ${GREEN}✓${NC} PWA + API responden"
    else
        echo -e "  ${RED}✗${NC} PWA/API no responden en https://localhost:3000"
    fi
    echo -e "  PWA:  https://$(hostname).local:3000   ·   https://$(hostname -I | awk '{print $1}'):3000"
    echo -e "  API:  http://$(hostname).local:8000/docs"
}

enable_services() {
    show_header
    echo -e "${BLUE}Habilitando inicio automático al boot...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        systemctl --user enable "$service" 2>/dev/null && ok_mark || fail_mark
    done
    echo -ne "  ▸ biomed-edge (autoarranque del escritorio)... "
    autostart_enable && ok_mark || fail_mark
    echo ""
    echo -e "${GREEN}✓ Inicio automático habilitado${NC}"
    if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
        echo -e "${YELLOW}⚠ Linger desactivado: los servicios arrancarán al iniciar sesión, no al encender.${NC}"
        echo -e "${YELLOW}  Actívalo con: sudo loginctl enable-linger $USER${NC}"
    else
        echo -e "${YELLOW}Los servicios arrancarán automáticamente al encender la Pi${NC}"
    fi
}

disable_services() {
    show_header
    echo -e "${YELLOW}Deshabilitando inicio automático...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        systemctl --user disable "$service" 2>/dev/null && ok_mark || fail_mark
    done
    echo -ne "  ▸ biomed-edge (autoarranque del escritorio)... "
    rm -f "$AUTOSTART_FILE" && ok_mark
    echo ""
    echo -e "${GREEN}✓ Inicio automático deshabilitado${NC}"
    echo -e "${YELLOW}Útil para desarrollo: servicios NO arrancan al boot${NC}"
}

check_enabled() {
    show_header
    echo -e "${BLUE}Estado de inicio automático:${NC}"
    echo ""
    for service in $SERVICES; do
        if systemctl --user is-enabled --quiet "$service" 2>/dev/null; then
            echo -e "  ${GREEN}✓ Habilitado${NC}    - $service"
        else
            echo -e "  ${RED}✗ Deshabilitado${NC} - $service"
        fi
    done
    if [ -f "$AUTOSTART_FILE" ]; then
        echo -e "  ${GREEN}✓ Habilitado${NC}    - biomed-edge (autoarranque del escritorio)"
    else
        echo -e "  ${RED}✗ Deshabilitado${NC} - biomed-edge (autoarranque del escritorio)"
    fi
    echo ""
    if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" = "yes" ]; then
        echo -e "  ${GREEN}✓${NC} Linger activo (arrancan al encender, sin iniciar sesión)"
    else
        echo -e "  ${YELLOW}⚠${NC} Linger inactivo: sudo loginctl enable-linger $USER"
    fi
}

follow_logs() {
    case "$1" in
        edge)
            mkdir -p "$LOG_DIR"; touch "$LOG_DIR/edge.log"
            tail -n 50 -f "$LOG_DIR/edge.log" ;;
        mqtt-subscriber|fastapi|pwa)
            journalctl --user -u "biomed-$1" -n 50 -f ;;
        *)
            echo "Uso: $0 logs {edge|mqtt-subscriber|fastapi|pwa}"; return 1 ;;
    esac
}

show_logs() {
    show_header
    echo -e "${BLUE}Selecciona servicio para ver logs:${NC}"
    echo ""
    echo -e "${GREEN}[1]${NC} Edge UI"
    echo -e "${GREEN}[2]${NC} MQTT Subscriber"
    echo -e "${GREEN}[3]${NC} FastAPI"
    echo -e "${GREEN}[4]${NC} PWA"
    echo -e "${RED}[0]${NC} Volver"
    echo ""
    echo -ne "${BLUE}Opción:${NC} "
    read log_choice

    case $log_choice in
        1) service_name="edge" ;;
        2) service_name="mqtt-subscriber" ;;
        3) service_name="fastapi" ;;
        4) service_name="pwa" ;;
        0) return ;;
        *) echo -e "${RED}Opción inválida${NC}"; sleep 2; return ;;
    esac

    show_header
    echo -e "${BLUE}Logs de biomed-${service_name} (Ctrl+C para salir):${NC}"
    echo ""
    follow_logs "$service_name"
}

reinstall_services() {
    show_header
    echo -e "${BLUE}Reinstalando servicios...${NC}"
    echo ""
    echo -ne "▸ Archivos de servicio (~/.config/systemd/user)... "
    install_services && ok_mark || fail_mark
    if [ -f "$AUTOSTART_FILE" ]; then
        echo -ne "▸ Autoarranque de Edge UI... "
        autostart_enable && ok_mark
    fi
    echo ""
    echo -e "${GREEN}✓ Servicios reinstalados correctamente${NC}"
}

build_pwa() {
    show_header
    echo -e "${BLUE}Recompilando PWA (producción)...${NC}"
    mkdir -p "$LOG_DIR"
    if (cd "$WEBAPP_DIR" && npm run build > "$LOG_DIR/build.log" 2>&1); then
        echo -e "  ${GREEN}✓${NC} Compilación correcta"
        echo -ne "  ▸ Reiniciando biomed-pwa... "
        systemctl --user restart biomed-pwa && ok_mark || fail_mark
    else
        echo -e "  ${RED}✗ Falló la compilación:${NC}"
        tail -20 "$LOG_DIR/build.log"
        return 1
    fi
}

clean_logs() {
    show_header
    echo -e "${BLUE}Limpiando logs antiguos...${NC}"
    find "$LOG_DIR" -name '*.log' -type f -exec truncate -s 0 {} + 2>/dev/null
    journalctl --user --vacuum-time=7d 2>/dev/null || sudo journalctl --vacuum-time=7d
    echo ""
    echo -e "${GREEN}✓ Logs limpiados${NC}"
}

pause() {
    echo ""
    echo -ne "${CYAN}Presiona Enter para continuar...${NC}"
    read
}

# Main loop interactivo
interactive_mode() {
    while true; do
        show_menu
        read choice

        case $choice in
            1) start_services; pause ;;
            2) stop_services; pause ;;
            3) restart_services; pause ;;
            4) status_services; pause ;;
            5) enable_services; pause ;;
            6) disable_services; pause ;;
            7) check_enabled; pause ;;
            8) show_logs ;;
            9) reinstall_services; pause ;;
            10) clean_logs; pause ;;
            11) build_pwa; pause ;;
            0)
                show_header
                echo -e "${GREEN}¡Hasta luego!${NC}"
                echo ""
                exit 0
                ;;
            *)
                echo -e "${RED}Opción inválida${NC}"
                sleep 1
                ;;
        esac
    done
}

# Si se llama sin argumentos, modo interactivo
if [ $# -eq 0 ]; then
    interactive_mode
else
    # Modo comando (compatibilidad con scripts)
    case "$1" in
        start) start_services ;;
        stop) stop_services ;;
        restart) restart_services ;;
        status) status_services ;;
        enable) enable_services ;;
        disable) disable_services ;;
        check) check_enabled ;;
        install) install_services ;;
        reinstall) reinstall_services ;;
        build) build_pwa ;;
        logs)
            if [ -z "${2:-}" ]; then
                show_logs
            else
                follow_logs "$2"
            fi
            ;;
        clean) clean_logs ;;
        edge-start) edge_start ;;
        edge-stop) edge_stop ;;
        *)
            echo "Uso: $0 {start|stop|restart|status|enable|disable|check|reinstall|build|logs|clean}"
            echo "O ejecuta sin argumentos para modo interactivo"
            exit 1
            ;;
    esac
fi
