# 🩺 BioMed Pi5 — Guía de Uso Rápido

---

## 🚀 Inicio Rápido

### Un solo comando

```bash
/home/harlink/biomed-pi5/start_biomed.sh
```

O **doble click** en el ícono del escritorio: `Biomed-Pi5`

Esto abre automáticamente:
- ✅ Edge UI (PyQt6) - Interfaz con sensores
- ✅ MQTT Subscriber - Sincronización de datos
- ✅ Raw Sync Service - Sincronización de señales
- ✅ FastAPI - API REST (puerto 8000)

### Detener todos los servicios

```bash
/home/harlink/biomed-pi5/stop_biomed.sh
```

---

## 📱 Acceder desde tu Celular/PC

### Webapp (PWA)

**Modo desarrollo** (con hot reload, cambios se ven instantáneos):
```bash
cd /home/harlink/biomed-pi5/services/webapp
npm run dev
```
Abre: `http://harlink.local:3000`

**Modo producción** (para instalar como app en el celular):
```bash
cd /home/harlink/biomed-pi5/services/webapp
npm run build && node start-https.mjs
```
Abre: `https://harlink.local:3000`

### API (FastAPI)

Documentación interactiva: `http://harlink.local:8000/docs`

---

## 📲 Instalar PWA como App

### Requisito
La PWA debe estar en **modo producción** (`node start-https.mjs`), no en modo dev.

### Android (Chrome)
1. Abre `https://harlink.local:3000`
2. Advertencia de seguridad → **"Avanzado"** → **"Continuar de todas formas"**
3. Menú (⋮) → **"Agregar a pantalla de inicio"**

### iPhone (Safari)
1. Abre `https://harlink.local:3000`
2. Advertencia → **"Mostrar detalles"** → **"Visitar este sitio web"**
3. Compartir (⬆) → **"Agregar a pantalla de inicio"**

---

## 🔍 Verificar que Todo Funciona

### Checklist rápido

```bash
# 1. API responde
curl http://harlink.local:8000/health

# 2. Mosquitto corriendo
sudo systemctl status mosquitto

# 3. Ver mensajes MQTT en tiempo real
mosquitto_sub -h localhost -t 'biomed/pi5-001/#' -v

# 4. Ver últimas mediciones
sqlite3 /home/harlink/biomed-pi5/data/storage.db \
  "SELECT id, spo2_pct, hr_bpm FROM spo2_measurements ORDER BY id DESC LIMIT 3"
```

---

## 🌐 Red

### Usando mDNS (recomendado)
- **Hostname:** `harlink.local`
- **Ventaja:** Funciona en cualquier red WiFi sin reconfigurar
- **URLs:** 
  - PWA: `https://harlink.local:3000`
  - API: `http://harlink.local:8000`

### Si mDNS no funciona
Usa la IP directa:

```bash
# Ver IP actual
hostname -I
```

Luego accede por IP:
- PWA: `https://192.168.1.X:3000`
- API: `http://192.168.1.X:8000`

---

## 🔧 Uso Manual (Avanzado)

Si necesitas iniciar servicios uno por uno:

### Edge UI
```bash
cd /home/harlink/biomed-pi5
source .venv/bin/activate
python main.py
```

### MQTT Subscriber
```bash
cd /home/harlink/biomed-pi5/services
source ../.venv/bin/activate
python mqtt_subscriber.py
```

### Raw Sync Service
```bash
cd /home/harlink/biomed-pi5/services
source ../.venv/bin/activate
python raw_sync_service.py
```

### FastAPI
```bash
cd /home/harlink/biomed-pi5/services/storage
source ../../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### PWA
```bash
cd /home/harlink/biomed-pi5/services/webapp

# Desarrollo (hot reload)
npm run dev

# Producción (instalable)
npm run build && node start-https.mjs
```

---

## 🐛 Problemas Comunes

| Problema | Solución |
|----------|----------|
| `EADDRINUSE: port 3000` | `fuser -k 3000/tcp` |
| `EADDRINUSE: port 8000` | `fuser -k 8000/tcp` |
| PWA no carga en celular | Verifica que celular y Pi estén en el mismo WiFi |
| "Sitio no seguro" en Chrome | Normal con certificado local. Toca "Avanzado" → "Continuar" |
| Edge no guarda datos | Verifica que aparezca `[Storage] Timers inicializados` en logs |
| MQTT desconectado | `sudo systemctl restart mosquitto` |
| Cambios en PWA no se ven | En dev: automático. En prod: `npm run build` de nuevo |
| mDNS no resuelve `harlink.local` | Usa IP directa: `hostname -I` |

---

## 📊 ¿Qué Datos se Guardan?

### En tiempo real vía MQTT
- Temperatura corporal (cada 10s si persona detectada)
- SpO2 y frecuencia cardíaca (cada 90s)
- Presión arterial (bajo demanda)
- Señales raw (IR/Red de SpO2, presión/oscilaciones de BP)

### Dos bases de datos
- **biomed.db** - Local en Edge (guardado rápido)
- **storage.db** - Permanente para API/PWA (replicado vía MQTT)

Si MQTT falla, los datos se reintentan automáticamente cada 30s.

---

## 🔄 Flujo de Trabajo Típico

### Desarrollo diario
```bash
# Iniciar servicios core
./start_biomed.sh

# Desarrollar PWA (en otra terminal)
cd services/webapp
npm run dev
# → Los cambios se ven instantáneamente en http://harlink.local:3000
```

### Probar en celular
```bash
# Build (solo cuando cambies código)
cd services/webapp
npm run build

# Iniciar con HTTPS
node start-https.mjs

# Instalar PWA
# https://harlink.local:3000 → Agregar a pantalla de inicio
```

### Al terminar
```bash
./stop_biomed.sh
```

---

## 📁 Archivos Importantes
biomed-pi5/
├── start_biomed.sh          # ← Iniciar todo
├── stop_biomed.sh           # ← Detener todo
├── INSTRUCTIVO.md           # ← Este archivo
├── STRUCTURE.md             # ← Arquitectura técnica detallada
│
├── config/
│   ├── settings.yaml        # ← Configuración sensores/MQTT
│   └── patient.json         # ← Datos del paciente
│
├── data/
│   ├── biomed.db            # ← DB local
│   └── storage.db           # ← DB permanente
│
└── services/webapp/
├── start-https.mjs      # ← Servidor HTTPS para producción
└── .env.local           # ← URL de la API
---

## 🎯 URLs Útiles

| Servicio | URL | Cuándo usar |
|----------|-----|-------------|
| PWA Dev | http://harlink.local:3000 | Desarrollo con hot reload |
| PWA Prod | https://harlink.local:3000 | Instalación en celular |
| API Docs | http://harlink.local:8000/docs | Ver endpoints disponibles |
| API Health | http://harlink.local:8000/health | Verificar que API funciona |

---

## ⚙️ Comandos Útiles

```bash
# Ver procesos corriendo
ps aux | grep -E "biomed|mqtt|uvicorn"

# Ver qué usa un puerto
fuser 3000/tcp
fuser 8000/tcp

# Ver IP actual
hostname -I

# Reiniciar MQTT broker
sudo systemctl restart mosquitto

# Ver mensajes MQTT en vivo
mosquitto_sub -h localhost -t 'biomed/pi5-001/#' -v

# Ver últimas mediciones en DB
sqlite3 data/storage.db \
  "SELECT * FROM spo2_measurements ORDER BY id DESC LIMIT 5"
```

---

## 🔐 Certificado HTTPS

El certificado es válido solo para desarrollo local. Los navegadores mostrarán advertencia de seguridad — es normal.

### Regenerar si cambias de red/hostname

```bash
cd services/webapp
mkcert harlink.local
# O con IP: mkcert 192.168.1.75

# Actualizar start-https.mjs con el nuevo nombre
nano start-https.mjs
```

---

## 📖 Documentación Adicional

- **STRUCTURE.md** - Arquitectura completa del sistema
- **README.md** - Descripción general del proyecto
- **config/settings.yaml** - Configuración detallada de sensores

---

**¿Dudas?** Revisa los logs en las terminales donde corren los servicios.

**Última actualización:** Mayo 2026
