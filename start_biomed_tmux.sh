#!/bin/bash
# Inicia todos los servicios en tmux

SESSION="biomed"
PROJECT_DIR="/home/harlink/biomed-pi5"

# Matar sesión anterior si existe
tmux kill-session -t $SESSION 2>/dev/null

# Crear sesión tmux
tmux new-session -d -s $SESSION -n "edge" -c "$PROJECT_DIR"

# Ventana 1 - Edge
tmux send-keys -t $SESSION:edge "source .venv/bin/activate && python main.py" C-m

# Ventana 2 - MQTT Subscriber
tmux new-window -t $SESSION -n "mqtt-sub" -c "$PROJECT_DIR/services"
tmux send-keys -t $SESSION:mqtt-sub "source ../.venv/bin/activate && python mqtt_subscriber.py" C-m

# Ventana 3 - FastAPI
tmux new-window -t $SESSION -n "fastapi" -c "$PROJECT_DIR/services/storage"
tmux send-keys -t $SESSION:fastapi "source ../../.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload" C-m

# Ventana 4 - PWA
tmux new-window -t $SESSION -n "pwa" -c "$PROJECT_DIR/services/webapp"
tmux send-keys -t $SESSION:pwa "npm run dev" C-m

# Volver a la primera ventana
tmux select-window -t $SESSION:edge

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Sesión tmux 'biomed' creada"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Para conectarte:"
echo "  tmux attach -t biomed"
echo ""
echo "Navegación tmux:"
echo "  Ctrl+B luego 0-3  → cambiar ventana"
echo "  Ctrl+B luego d    → detach (deja corriendo)"
echo ""
echo "Para detener todo:"
echo "  tmux kill-session -t biomed"

# Adjuntar a la sesión
tmux attach-session -t $SESSION
