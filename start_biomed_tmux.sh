#!/bin/bash
# Inicia todos los servicios en tmux

SESSION="biomed"
PROJECT_DIR="/home/harlink/biomed-pi5"

# Crear sesión tmux
tmux new-session -d -s $SESSION -n "edge" -c "$PROJECT_DIR"

# Ventana 1 - Edge
tmux send-keys -t $SESSION:edge "source .venv/bin/activate && python main.py" C-m

# Ventana 2 - MQTT Subscriber
tmux new-window -t $SESSION -n "mqtt-sub" -c "$PROJECT_DIR/services"
tmux send-keys -t $SESSION:mqtt-sub "source ../.venv/bin/activate && python mqtt_subscriber.py" C-m

# Ventana 3 - Raw Sync
tmux new-window -t $SESSION -n "raw-sync" -c "$PROJECT_DIR/services"
tmux send-keys -t $SESSION:raw-sync "source ../.venv/bin/activate && python raw_sync_service.py" C-m

# Ventana 4 - FastAPI
tmux new-window -t $SESSION -n "fastapi" -c "$PROJECT_DIR/services/storage"
tmux send-keys -t $SESSION:fastapi "source ../../.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload" C-m

# Ventana 5 - PWA
tmux new-window -t $SESSION -n "pwa" -c "$PROJECT_DIR/services/webapp"
tmux send-keys -t $SESSION:pwa "node start-https.mjs" C-m

# Volver a la primera ventana
tmux select-window -t $SESSION:edge

# Adjuntar a la sesión
tmux attach-session -t $SESSION
