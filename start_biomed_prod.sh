#!/bin/bash
# Script para PRODUCCIÓN - PWA instalable
#
# Los 3 servicios de fondo (MQTT subscriber, FastAPI, PWA HTTPS compilada)
# corren como servicios systemd de usuario y la Edge UI con el autoarranque
# del escritorio (ver biomed-control.sh). Este script los (re)inicia — también
# detiene los procesos del modo DESARROLLO si estaban abiertos — y muestra
# el estado en una terminal.

PROJECT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
CONTROL="$PROJECT_DIR/biomed-control.sh"

run() {
    "$CONTROL" restart
    sleep 3
    "$CONTROL" status
    echo ""
    echo "✓ Modo PRODUCCIÓN — PWA instalable en el celular"
}

if [ -t 1 ] || [ -z "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]; then
    run
else
    # Lanzado desde el ícono del escritorio (sin terminal): abrir una
    export -f run; export CONTROL
    lxterminal --title="Biomed Pi5 - Producción" \
      -e bash -c 'run; echo; read -p "Enter para cerrar esta ventana (los servicios siguen corriendo)"'
fi
