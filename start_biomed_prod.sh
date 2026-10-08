#!/bin/bash
# Script para PRODUCCIÓN - PWA instalable

PROJECT_DIR="/home/harlink/biomed-pi5"

echo "=========================================="
echo "   Biomed Pi5 - MODO PRODUCCIÓN"
echo "=========================================="

# Terminal 1 - Edge UI
lxterminal --title="Biomed - Edge UI" \
  --working-directory="$PROJECT_DIR" \
  -e "bash -c 'source .venv/bin/activate && python main.py; exec bash'" &
sleep 2

# Terminal 2 - MQTT Subscriber
lxterminal --title="Biomed - MQTT Subscriber" \
  --working-directory="$PROJECT_DIR/services" \
  -e "bash -c 'source ../.venv/bin/activate && python mqtt_subscriber.py; exec bash'" &
sleep 2

# Terminal 3 - FastAPI
lxterminal --title="Biomed - FastAPI" \
  --working-directory="$PROJECT_DIR/services/storage" \
  -e "bash -c 'source ../../.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload; exec bash'" &
sleep 2

# Terminal 4 - PWA en PRODUCCIÓN
echo "[4/4] Iniciando PWA (Producción - HTTPS)..."
lxterminal --title="Biomed - PWA (HTTPS)" \
  --working-directory="$PROJECT_DIR/services/webapp" \
  -e "bash -c 'node start-https.mjs; exec bash'" &

echo ""
echo "✓ Modo PRODUCCIÓN iniciado"
echo ""
echo "Acceso PWA: https://harlink.local:3000"
echo "  (Instalable en celular)"
echo ""
echo "API Docs: http://harlink.local:8000/docs"
