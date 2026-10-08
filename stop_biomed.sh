#!/bin/bash
# Script para detener todos los servicios de biomed-pi5

echo "Deteniendo servicios Biomed Pi5..."

# Primero los servicios systemd: si solo se matan los procesos, systemd los
# vuelve a levantar a los 5 s (Restart=always)
"$(dirname "$(readlink -f "$0")")/biomed-control.sh" stop > /dev/null 2>&1

# Procesos del modo desarrollo, por nombre
pkill -f "python.*main.py"
pkill -f "python.*mqtt_subscriber"
pkill -f "uvicorn.*main:app"
pkill -f "node.*start-https"
pkill -f "npm.*run.*dev"

# Liberar puertos
fuser -k 8000/tcp 2>/dev/null
fuser -k 3000/tcp 2>/dev/null

echo "✓ Todos los servicios detenidos"
