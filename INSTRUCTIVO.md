# 🩺 BioMed Pi5 — Guía de Uso Rápido

Sistema IoT de monitoreo biomédico con arquitectura MQTT para replicación de datos en tiempo real.

---

## 🎯 Inicio Rápido

### Opción 1: Script Helper (Recomendado)

```bash
cd /home/harlink/biomed-pi5
./biomed-control.sh start
```

Esto inicia los 5 servicios:
- ✅ Edge UI (PyQt6)
- ✅ MQTT Subscriber
- ✅ Raw Sync Service
- ✅ FastAPI (puerto 8000)
- ✅ PWA Producción HTTPS (puerto 3000)

### Opción 2: Íconos del Escritorio

**Doble click en:**
- 💚 **Biomed Pi5 (DESARROLLO)** → Modo dev con hot reload
- 🚀 **Biomed Pi5 (PRODUCCIÓN)** → Modo producción con HTTPS

---

## 🔧 Script Helper - biomed-control.sh

Herramienta todo-en-uno para gestionar los servicios del sistema.

### Comandos Principales

```bash
# Iniciar todos los servicios
./biomed-control.sh start

# Detener todos los servicios
./biomed-control.sh stop

# Reiniciar todos los servicios
./biomed-control.sh restart

# Ver estado de todos los servicios
./biomed-control.sh status
```

### Auto-arranque (Boot)

**Habilitar inicio automático** (arrancan al encender la Pi):
```bash
./biomed-control.sh enable
```

**Deshabilitar inicio automático** (útil cuando estás programando):
```bash
./biomed-control.sh disable
```

**Verificar qué está habilitado:**
```bash
./biomed-control.sh check
```

### Mantenimiento

**Ver logs en tiempo real:**
```bash
# Logs de Edge UI
./biomed-control.sh logs edge

# Logs de MQTT Subscriber
./biomed-control.sh logs mqtt-subscriber

# Logs de FastAPI
./biomed-control.sh logs fastapi

# Logs de PWA
./biomed-control.sh logs pwa

# Logs de Raw Sync
./biomed-control.sh logs raw-sync
```

**Reinstalar servicios systemd** (si algo crashea):
```bash
./biomed-control.sh reinstall
```

**Limpiar logs antiguos:**
```bash
./biomed-control.sh clean
```

**Ver ayuda completa:**
```bash
./biomed-control.sh help
```

---

## 🏗️ Servicios del Sistema

El sistema está compuesto por 5 servicios independientes gestionados por systemd:

| Servicio | Descripción | Puerto |
|----------|-------------|--------|
| **biomed-edge** | Interfaz PyQt6, lee sensores físicos | Display |
| **biomed-mqtt-subscriber** | Replica datos procesados → storage.db | - |
| **biomed-raw-sync** | Sincroniza señales raw cada 30s | - |
| **biomed-fastapi** | API REST para PWA | 8000 |
| **biomed-pwa** | PWA modo producción (HTTPS) | 3000 |

### Dependencias entre servicios
Edge → MQTT Broker → Subscriber → storage.db → FastAPI → PWA
↓
Raw Sync → storage.db
---

## 📱 Acceso desde Otros Dispositivos

### URLs de Acceso

| Servicio | URL | Cuándo usar |
|----------|-----|-------------|
| PWA Prod | https://harlink.local:3000 | Modo producción (instalable) |
| PWA Dev | http://harlink.local:3000 | Desarrollo con hot reload |
| API Docs | http://harlink.local:8000/docs | Swagger UI interactivo |
| API Health | http://harlink.local:8000/health | Verificar funcionamiento |

### Instalar PWA en Celular

**Requisitos:**
- PWA en modo producción (`biomed-pwa.service` corriendo)
- Celular y Pi en la misma red WiFi

**Android (Chrome):**
1. Abre `https://harlink.local:3000`
2. Advertencia de seguridad → **"Avanzado"** → **"Continuar de todas formas"**
3. Menú (⋮) → **"Agregar a pantalla de inicio"**

**iPhone (Safari):**
1. Abre `https://harlink.local:3000`
2. Advertencia → **"Mostrar detalles"** → **"Visitar este sitio web"**
3. Compartir (⬆) → **"Agregar a pantalla de inicio"**

---

## 🔄 Flujo de Trabajo

### Para Presentaciones / Demos

```bash
# 1. Habilitar auto-arranque
./biomed-control.sh enable

# 2. Reiniciar Pi
sudo reboot

# Todo arranca automáticamente en modo producción
# PWA instalable: https://harlink.local:3000
```

### Para Desarrollo / Programación

```bash
# 1. Deshabilitar auto-arranque (no estorba al programar)
./biomed-control.sh disable

# 2. Cuando necesites probar, inicia manualmente
./biomed-control.sh start

# 3. Desarrollar PWA con hot reload
cd services/webapp
npm run dev
# http://harlink.local:3000
```

---

## 💾 Cierre de Sesión

Las sesiones se cierran automáticamente de 2 formas:

### 1️⃣ Botón Manual (en Edge UI)

1. Ve al tab **Paciente** (👤)
2. Click en **"🔒 Cerrar Sesión"**
3. La sesión se cierra en `biomed.db` y se publica a MQTT
4. MQTT Subscriber replica el cierre a `storage.db`
5. PWA actualiza automáticamente

### 2️⃣ Al Cerrar Edge

Al cerrar la ventana de Edge (X o Alt+F4):
- Se ejecuta `closeEvent`
- Cierra la sesión activa
- Se publica a MQTT
- Se replica a `storage.db`

**No más sesiones "En curso" huérfanas.**

---

## 🗄️ Bases de Datos

### biomed.db (Edge - Local)
- **Ubicación:** `/home/harlink/biomed-pi5/data/biomed.db`
- **Función:** Almacenamiento local rápido
- **Store-and-forward:** Datos con `synced=0` se reintentan vía MQTT

### storage.db (API - Permanente)
- **Ubicación:** `/home/harlink/biomed-pi5/data/storage.db`
- **Función:** Datos replicados vía MQTT para API/PWA
- **Acceso:** FastAPI lee de aquí

### Ver Datos

```bash
# Últimas mediciones de SpO2 (biomed.db)
sqlite3 /home/harlink/biomed-pi5/data/biomed.db \
  "SELECT id, ts, spo2_pct, hr_bpm FROM spo2_measurements ORDER BY id DESC LIMIT 5"

# Últimas mediciones de SpO2 (storage.db)
sqlite3 /home/harlink/biomed-pi5/data/storage.db \
  "SELECT id, ts, spo2_pct, hr_bpm FROM spo2_measurements ORDER BY id DESC LIMIT 5"

# Ver sesiones abiertas
sqlite3 /home/harlink/biomed-pi5/data/storage.db \
  "SELECT id, started_at, ended_at FROM sessions WHERE ended_at IS NULL"
```

---

## 🔌 MQTT

### Broker: Mosquitto

```bash
# Estado del broker
sudo systemctl status mosquitto

# Reiniciar
sudo systemctl restart mosquitto
```

### Topics
biomed/pi5-001/temp         ← Temperatura corporal
biomed/pi5-001/spo2         ← SpO2 + HR (con señales raw IR/Red)
biomed/pi5-001/bp           ← Presión arterial (con señales raw)
biomed/pi5-001/session/end  ← Cierre de sesión
### Monitorear Mensajes

```bash
# Ver todos los mensajes en tiempo real
mosquitto_sub -h localhost -t 'biomed/pi5-001/#' -v

# Ver solo temperatura
mosquitto_sub -h localhost -t 'biomed/pi5-001/temp' -v

# Ver solo cierres de sesión
mosquitto_sub -h localhost -t 'biomed/pi5-001/session/end' -v
```

---

## 🌐 Red

### mDNS (Recomendado)

- **Hostname:** `harlink.local`
- **Ventaja:** Funciona en cualquier red sin reconfigurar
- **Requisito:** Avahi corriendo

```bash
# Verificar Avahi
sudo systemctl status avahi-daemon

# Si no está activo
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

### IP Directa (Alternativa)

Si mDNS no funciona:

```bash
# Ver IP actual
hostname -I
```

Accede por IP: `http://192.168.1.X:3000`

---

## 🔧 Comandos Útiles

### Gestión de Servicios

```bash
# Ver estado detallado de un servicio
sudo systemctl status biomed-edge

# Reiniciar un servicio específico
sudo systemctl restart biomed-fastapi

# Ver logs con límite de líneas
sudo journalctl -u biomed-mqtt-subscriber -n 100

# Seguir logs en tiempo real
sudo journalctl -u biomed-edge -f
```

### Verificación de Funcionamiento

```bash
# API responde
curl http://harlink.local:8000/health

# MQTT broker activo
mosquitto_sub -h localhost -t '$SYS/broker/clients/connected' -C 1

# Ver procesos corriendo
ps aux | grep -E "biomed|uvicorn|mqtt"

# Ver puertos abiertos
sudo lsof -i :3000
sudo lsof -i :8000
sudo lsof -i :1883
```

---

## 🐛 Troubleshooting

### Servicios no arrancan

```bash
# Ver logs detallados
./biomed-control.sh logs edge

# Reinstalar servicios
./biomed-control.sh reinstall

# Verificar permisos
ls -l /home/harlink/biomed-pi5/
```

### Edge no aparece en pantalla

```bash
# Verificar DISPLAY
echo $DISPLAY  # Debe ser :0

# Verificar permisos X11
xhost +local:

# Reiniciar servicio
sudo systemctl restart biomed-edge
```

### PWA no carga

```bash
# Verificar que PWA esté corriendo
./biomed-control.sh status

# Ver logs de PWA
./biomed-control.sh logs pwa

# Verificar certificado
ls -l /home/harlink/biomed-pi5/services/webapp/*.pem
```

### MQTT no sincroniza

```bash
# Verificar Mosquitto
sudo systemctl status mosquitto

# Ver mensajes MQTT
mosquitto_sub -h localhost -t 'biomed/pi5-001/#' -v

# Reiniciar subscriber
sudo systemctl restart biomed-mqtt-subscriber

# Ver logs del subscriber
./biomed-control.sh logs mqtt-subscriber
```

### Sesiones "En curso"

```bash
# Ver sesiones abiertas
sqlite3 /home/harlink/biomed-pi5/data/storage.db \
  "SELECT id, started_at, ended_at FROM sessions WHERE ended_at IS NULL"

# Cerrar manualmente
cd /home/harlink/biomed-pi5
source .venv/bin/activate
python tools/close_open_sessions.py
python tools/sync_sessions.py
```

---

## 📁 Estructura del Proyecto
biomed-pi5/
├── biomed-control.sh        # ← Script helper principal
├── start_biomed.sh          # ← Launcher modo desarrollo
├── start_biomed_prod.sh     # ← Launcher modo producción
├── stop_biomed.sh           # ← Detener servicios manuales
├── main.py                  # ← Entry point Edge UI
├── INSTRUCTIVO.md           # ← Este archivo
├── STRUCTURE.md             # ← Arquitectura técnica
│
├── config/
│   ├── settings.yaml        # ← Configuración sensores/MQTT
│   └── patient.json         # ← Datos del paciente
│
├── data/
│   ├── biomed.db            # ← DB local Edge
│   └── storage.db           # ← DB permanente API
│
├── tools/
│   ├── close_open_sessions.py  # ← Cerrar sesiones huérfanas
│   └── sync_sessions.py        # ← Sincronizar sesiones manual
│
└── services/
├── mqtt_subscriber.py      # ← Replica MQTT → storage.db
├── raw_sync_service.py     # ← Sincroniza raw cada 30s
├── storage/                # ← FastAPI
│   └── main.py
└── webapp/                 # ← Next.js PWA
└── start-https.mjs
---

## 📊 Datos que se Sincronizan

### Vía MQTT en Tiempo Real

- ✅ Temperatura corporal (cada 10s si persona detectada)
- ✅ SpO2 y HR procesados (cada 90s)
- ✅ Presión arterial procesada (bajo demanda)
- ✅ Señales raw SpO2 (IR, Red, umbrales)
- ✅ Señales raw BP (presión, oscilaciones, envolvente)
- ✅ **Cierre de sesión** (automático vía MQTT)

### ⚠️ Aclaración Importante: TODO va por MQTT

**No hay conexión directa entre `biomed.db` y `storage.db`.**

Todos los datos (procesados y raw) viajan vía MQTT:

1. **Edge** guarda en `biomed.db` + publica a MQTT
2. **MQTT Broker** (Mosquitto) distribuye los mensajes
3. **Subscriber** recibe y guarda en `storage.db`

**Raw Sync Service** NO copia entre DBs, sino que:
- Lee raw con `synced=0` de `biomed.db`
- **RE-PUBLICA a MQTT** (retry)
- Subscriber los recibe y guarda en `storage.db`

**Todo pasa por MQTT.** Store-and-forward garantiza que nada se pierda.

### Store-and-Forward Automático

Si MQTT falla temporalmente:
- Datos procesados: reintentan cada 30s
- Datos raw: reintentan cada 30s
- Cierres de sesión: se publican al reconectar

---

## ✅ Checklist Pre-Uso

Antes de una presentación o demo:

- [ ] Pi encendida y conectada a WiFi
- [ ] Auto-arranque habilitado: `./biomed-control.sh check`
- [ ] Sensores conectados correctamente
- [ ] Mosquitto corriendo: `sudo systemctl status mosquitto`
- [ ] Todos los servicios activos: `./biomed-control.sh status`
- [ ] PWA accesible: `https://harlink.local:3000`
- [ ] FastAPI responde: `http://harlink.local:8000/health`

---

## 🎓 Modo Desarrollo vs Producción

### Modo Desarrollo

```bash
# Deshabilitar auto-arranque
./biomed-control.sh disable

# Iniciar servicios core
./biomed-control.sh start

# PWA con hot reload
cd services/webapp
npm run dev
# http://harlink.local:3000
```

**Ventajas:**
- Hot reload instantáneo
- Cambios se ven sin rebuild
- No estorba al programar

### Modo Producción

```bash
# Habilitar auto-arranque
./biomed-control.sh enable

# Todo arranca al boot
sudo reboot

# PWA instalable
# https://harlink.local:3000
```

**Ventajas:**
- HTTPS con certificado
- PWA instalable en celular
- Optimizado y rápido
- Arranque automático

---

## 📞 Soporte

**Si algo no funciona:**

1. Ver logs: `./biomed-control.sh logs [servicio]`
2. Verificar estado: `./biomed-control.sh status`
3. Reinstalar servicios: `./biomed-control.sh reinstall`
4. Revisar STRUCTURE.md para detalles técnicos

**Archivos de log:**
```bash
# Ver logs del sistema
sudo journalctl -u biomed-* --since today

# Limpiar logs viejos
./biomed-control.sh clean
```

---

**Última actualización:** Mayo 2026  
**Versión:** 3.0 (Systemd + Auto-arranque + Script Helper)
