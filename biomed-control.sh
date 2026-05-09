#!/bin/bash
# Control de servicios Biomed Pi5
# Gestiona los 4 servicios systemd del sistema de monitoreo biomédico

SERVICES="biomed-mqtt-subscriber biomed-fastapi biomed-pwa biomed-edge"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

show_header() {
    clear
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
    echo -e "${CYAN}[9]${NC} 🔧 Reinstalar servicios systemd"
    echo -e "${CYAN}[10]${NC} 🧹 Limpiar logs antiguos"
    echo ""
    echo -e "${RED}[0]${NC} Salir"
    echo ""
    echo -ne "${BLUE}Selecciona una opción [0-10]:${NC} "
}

start_services() {
    show_header
    echo -e "${BLUE}Iniciando servicios Biomed Pi5...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        sudo systemctl start $service && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    done
    echo ""
    echo -e "${GREEN}✓ Proceso completado${NC}"
}

stop_services() {
    show_header
    echo -e "${YELLOW}Deteniendo servicios Biomed Pi5...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        sudo systemctl stop $service && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    done
    echo ""
    echo -e "${GREEN}✓ Servicios detenidos${NC}"
}

restart_services() {
    show_header
    echo -e "${BLUE}Reiniciando servicios Biomed Pi5...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        sudo systemctl restart $service && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    done
    echo ""
    echo -e "${GREEN}✓ Servicios reiniciados${NC}"
}

status_services() {
    show_header
    echo -e "${BLUE}Estado de servicios:${NC}"
    echo ""
    for service in $SERVICES; do
        if systemctl is-active --quiet $service; then
            status="${GREEN}● Activo${NC}"
        else
            status="${RED}○ Inactivo${NC}"
        fi
        echo -e "  $status - $service"
    done
    echo ""
    echo -e "${CYAN}Presiona Enter para ver detalles completos...${NC}"
    read
    sudo systemctl status $SERVICES --no-pager
}

enable_services() {
    show_header
    echo -e "${BLUE}Habilitando inicio automático al boot...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        sudo systemctl enable $service && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    done
    echo ""
    echo -e "${GREEN}✓ Inicio automático habilitado${NC}"
    echo -e "${YELLOW}Los servicios arrancarán automáticamente al encender la Pi${NC}"
}

disable_services() {
    show_header
    echo -e "${YELLOW}Deshabilitando inicio automático...${NC}"
    echo ""
    for service in $SERVICES; do
        echo -ne "  ▸ ${service}... "
        sudo systemctl disable $service && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    done
    echo ""
    echo -e "${GREEN}✓ Inicio automático deshabilitado${NC}"
    echo -e "${YELLOW}Útil para desarrollo: servicios NO arrancan al boot${NC}"
}

check_enabled() {
    show_header
    echo -e "${BLUE}Estado de inicio automático:${NC}"
    echo ""
    for service in $SERVICES; do
        if systemctl is-enabled --quiet $service 2>/dev/null; then
            echo -e "  ${GREEN}✓ Habilitado${NC}  - $service"
        else
            echo -e "  ${RED}✗ Deshabilitado${NC} - $service"
        fi
    done
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
    sudo journalctl -u biomed-${service_name} -f
}

reinstall_services() {
    show_header
    echo -e "${YELLOW}¿Seguro que deseas reinstalar los servicios systemd?${NC}"
    echo -e "${YELLOW}Esto sobrescribirá los archivos existentes.${NC}"
    echo ""
    echo -ne "${BLUE}Continuar? [s/N]:${NC} "
    read confirm
    
    if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
        echo -e "${RED}Cancelado${NC}"
        sleep 1
        return
    fi
    
    show_header
    echo -e "${BLUE}Reinstalando archivos systemd...${NC}"
    echo ""
    
    # MQTT Subscriber
    echo -ne "▸ biomed-mqtt-subscriber.service... "
    sudo tee /etc/systemd/system/biomed-mqtt-subscriber.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Biomed Pi5 - MQTT Subscriber
After=network.target mosquitto.service
Requires=mosquitto.service

[Service]
Type=simple
User=harlink
WorkingDirectory=/home/harlink/biomed-pi5/services
ExecStart=/home/harlink/biomed-pi5/.venv/bin/python mqtt_subscriber.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOFSERVICE
    echo -e "${GREEN}✓${NC}"

    # FastAPI
    echo -ne "▸ biomed-fastapi.service... "
    sudo tee /etc/systemd/system/biomed-fastapi.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Biomed Pi5 - FastAPI REST API
After=network.target

[Service]
Type=simple
User=harlink
WorkingDirectory=/home/harlink/biomed-pi5/services/storage
ExecStart=/home/harlink/biomed-pi5/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOFSERVICE
    echo -e "${GREEN}✓${NC}"

    # PWA
    echo -ne "▸ biomed-pwa.service... "
    sudo tee /etc/systemd/system/biomed-pwa.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Biomed Pi5 - PWA (Producción HTTPS)
After=network.target

[Service]
Type=simple
User=harlink
WorkingDirectory=/home/harlink/biomed-pi5/services/webapp
ExecStart=/usr/bin/node start-https.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOFSERVICE
    echo -e "${GREEN}✓${NC}"

    # Edge UI
    echo -ne "▸ biomed-edge.service... "
    sudo tee /etc/systemd/system/biomed-edge.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Biomed Pi5 - Edge UI (PyQt6)
After=network.target graphical.target
Wants=graphical.target

[Service]
Type=simple
User=harlink
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/harlink/.Xauthority"
WorkingDirectory=/home/harlink/biomed-pi5
ExecStart=/home/harlink/biomed-pi5/.venv/bin/python /home/harlink/biomed-pi5/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOFSERVICE
    echo -e "${GREEN}✓${NC}"

    # Recargar systemd
    echo ""
    echo -ne "▸ Recargando systemd daemon... "
    sudo systemctl daemon-reload && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
    
    echo ""
    echo -e "${GREEN}✓ Servicios reinstalados correctamente${NC}"
}

clean_logs() {
    show_header
    echo -e "${YELLOW}Limpiando logs antiguos (conservando últimos 7 días)...${NC}"
    echo ""
    sudo journalctl --vacuum-time=7d
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
        reinstall) reinstall_services ;;
        logs) 
            if [ -z "$2" ]; then
                show_logs
            else
                sudo journalctl -u biomed-$2 -f
            fi
            ;;
        clean) clean_logs ;;
        *)
            echo "Uso: $0 {start|stop|restart|status|enable|disable|check|reinstall|logs|clean}"
            echo "O ejecuta sin argumentos para modo interactivo"
            exit 1
            ;;
    esac
fi
