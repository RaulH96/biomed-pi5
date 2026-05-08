#!/bin/bash
# Control de servicios Biomed Pi5
# Gestiona los 5 servicios systemd del sistema de monitoreo biomédico

SERVICES="biomed-mqtt-subscriber biomed-raw-sync biomed-fastapi biomed-pwa biomed-edge"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   🩺 Biomed Pi5 - Control de Servicios${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Uso: $0 {comando} [opciones]"
    echo ""
    echo -e "${GREEN}Comandos principales:${NC}"
    echo "  start              Inicia todos los servicios"
    echo "  stop               Detiene todos los servicios"
    echo "  restart            Reinicia todos los servicios"
    echo "  status             Muestra estado de todos los servicios"
    echo ""
    echo -e "${GREEN}Auto-arranque (boot):${NC}"
    echo "  enable             Habilita inicio automático al encender Pi"
    echo "  disable            Deshabilita inicio automático"
    echo "  check              Verifica qué servicios están habilitados"
    echo ""
    echo -e "${GREEN}Mantenimiento:${NC}"
    echo "  reinstall          Reinstala todos los archivos systemd"
    echo "  logs [servicio]    Muestra logs en tiempo real"
    echo "  clean              Limpia logs antiguos"
    echo ""
    echo -e "${GREEN}Servicios disponibles:${NC}"
    echo "  • biomed-edge              - Interfaz PyQt6 (lectura sensores)"
    echo "  • biomed-mqtt-subscriber   - Replica datos procesados a storage.db"
    echo "  • biomed-raw-sync          - Sincroniza señales raw cada 30s"
    echo "  • biomed-fastapi           - API REST (puerto 8000)"
    echo "  • biomed-pwa               - PWA modo producción HTTPS (puerto 3000)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 start           # Inicia todo"
    echo "  $0 enable          # Auto-arranque al boot"
    echo "  $0 disable         # Desactiva auto-arranque"
    echo "  $0 logs edge       # Ver logs de Edge UI"
    echo "  $0 reinstall       # Reinstalar servicios systemd"
}

start_services() {
    echo -e "${BLUE}Iniciando servicios Biomed Pi5...${NC}"
    for service in $SERVICES; do
        echo -e "  ▸ ${service}..."
        sudo systemctl start $service
    done
    echo -e "${GREEN}✓ Servicios iniciados${NC}"
}

stop_services() {
    echo -e "${YELLOW}Deteniendo servicios Biomed Pi5...${NC}"
    for service in $SERVICES; do
        echo -e "  ▸ ${service}..."
        sudo systemctl stop $service
    done
    echo -e "${GREEN}✓ Servicios detenidos${NC}"
}

restart_services() {
    echo -e "${BLUE}Reiniciando servicios Biomed Pi5...${NC}"
    for service in $SERVICES; do
        echo -e "  ▸ ${service}..."
        sudo systemctl restart $service
    done
    echo -e "${GREEN}✓ Servicios reiniciados${NC}"
}

status_services() {
    echo -e "${BLUE}Estado de servicios Biomed Pi5:${NC}"
    echo ""
    sudo systemctl status $SERVICES --no-pager
}

enable_services() {
    echo -e "${BLUE}Habilitando inicio automático al boot...${NC}"
    for service in $SERVICES; do
        echo -e "  ▸ ${service}..."
        sudo systemctl enable $service
    done
    echo -e "${GREEN}✓ Inicio automático habilitado${NC}"
    echo -e "${YELLOW}Los servicios arrancarán automáticamente al encender la Pi${NC}"
}

disable_services() {
    echo -e "${YELLOW}Deshabilitando inicio automático al boot...${NC}"
    for service in $SERVICES; do
        echo -e "  ▸ ${service}..."
        sudo systemctl disable $service
    done
    echo -e "${GREEN}✓ Inicio automático deshabilitado${NC}"
    echo -e "${YELLOW}Los servicios NO arrancarán al encender la Pi (útil para programar)${NC}"
}

check_enabled() {
    echo -e "${BLUE}Estado de inicio automático:${NC}"
    echo ""
    for service in $SERVICES; do
        if systemctl is-enabled --quiet $service 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} ${service} - ${GREEN}Habilitado${NC}"
        else
            echo -e "  ${RED}✗${NC} ${service} - ${RED}Deshabilitado${NC}"
        fi
    done
}

reinstall_services() {
    echo -e "${BLUE}Reinstalando archivos systemd...${NC}"
    echo ""
    
    # MQTT Subscriber
    echo "▸ Creando biomed-mqtt-subscriber.service..."
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

    # Raw Sync
    echo "▸ Creando biomed-raw-sync.service..."
    sudo tee /etc/systemd/system/biomed-raw-sync.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Biomed Pi5 - Raw Data Sync Service
After=network.target mosquitto.service
Requires=mosquitto.service

[Service]
Type=simple
User=harlink
WorkingDirectory=/home/harlink/biomed-pi5/services
ExecStart=/home/harlink/biomed-pi5/.venv/bin/python raw_sync_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOFSERVICE

    # FastAPI
    echo "▸ Creando biomed-fastapi.service..."
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

    # PWA
    echo "▸ Creando biomed-pwa.service..."
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

    # Edge UI
    echo "▸ Creando biomed-edge.service..."
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

    # Recargar systemd
    echo ""
    echo "▸ Recargando systemd daemon..."
    sudo systemctl daemon-reload
    
    echo ""
    echo -e "${GREEN}✓ Servicios reinstalados correctamente${NC}"
    echo -e "${YELLOW}Usa '$0 enable' para habilitar inicio automático${NC}"
}

show_logs() {
    local service_name="$1"
    if [ -z "$service_name" ]; then
        service_name="edge"
    fi
    
    echo -e "${BLUE}Logs de biomed-${service_name} (Ctrl+C para salir):${NC}"
    echo ""
    sudo journalctl -u biomed-${service_name} -f
}

clean_logs() {
    echo -e "${YELLOW}Limpiando logs antiguos...${NC}"
    sudo journalctl --vacuum-time=7d
    echo -e "${GREEN}✓ Logs limpiados (conservados últimos 7 días)${NC}"
}

# Main
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        status_services
        ;;
    enable)
        enable_services
        ;;
    disable)
        disable_services
        ;;
    check)
        check_enabled
        ;;
    reinstall)
        reinstall_services
        ;;
    logs)
        show_logs "$2"
        ;;
    clean)
        clean_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
