#!/bin/bash
# Script para iniciar todos los servicios de biomed-pi5

PROJECT_DIR="/home/harlink/biomed-pi5"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Iniciando Biomed Pi5 Services${NC}"
echo -e "${BLUE}========================================${NC}"

# Terminal 1 - Edge (PyQt6)
echo -e "${GREEN}[1/4] Iniciando Edge UI...${NC}"
lxterminal --title="Biomed - Edge UI" \
  --working-directory="$PROJECT_DIR" \
  -e "bash -c 'source .venv/bin/activate && python main.py; exec bash'" &
sleep 2

# Terminal 2 - MQTT Subscriber
echo -e "${GREEN}[2/4] Iniciando MQTT Subscriber...${NC}"
lxterminal --title="Biomed - MQTT Subscriber" \
  --working-directory="$PROJECT_DIR/services" \
  -e "bash -c 'source ../.venv/bin/activate && python mqtt_subscriber.py; exec bash'" &
sleep 2

# Terminal 3 - FastAPI
echo -e "${GREEN}[3/4] Iniciando FastAPI...${NC}"
lxterminal --title="Biomed - FastAPI" \
  --working-directory="$PROJECT_DIR/services/storage" \
  -e "bash -c 'source ../../.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload; exec bash'" &
sleep 2

# Terminal 4 - Next.js PWA
echo -e "${GREEN}[4/4] Iniciando PWA...${NC}"
lxterminal --title="Biomed - PWA" \
  --working-directory="$PROJECT_DIR/services/webapp" \
  -e "bash -c 'npm run dev; exec bash'" &
sleep 3

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Todos los servicios iniciados${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Servicios corriendo:"
echo "  • Edge UI (PyQt6)"
echo "  • MQTT Subscriber"
echo "  • FastAPI → http://harlink.local:8000/docs"
echo "  • PWA Dev → http://harlink.local:3000"
echo ""
echo -e "${YELLOW}Modo: DESARROLLO (hot reload)${NC}"
echo ""
echo "Para PWA en modo PRODUCCIÓN (instalable):"
echo "  cd $PROJECT_DIR/services/webapp"
echo "  npm run build && node start-https.mjs"
echo "  https://harlink.local:3000"
