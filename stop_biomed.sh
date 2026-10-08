#!/bin/bash
# Script para detener todos los servicios de biomed-pi5

echo "Deteniendo servicios Biomed Pi5..."

# Matar procesos por nombre
pkill -f "python.*main.py"
pkill -f "python.*mqtt_subscriber"
pkill -f "uvicorn.*main:app"
pkill -f "node.*start-https"
pkill -f "npm.*run.*dev"

# Liberar puertos
fuser -k 8000/tcp 2>/dev/null
fuser -k 3000/tcp 2>/dev/null

echo "✓ Todos los servicios detenidos"
