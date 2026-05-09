# 🏗️ BioMed Pi5 — Arquitectura Técnica

Documentación técnica completa del sistema de monitoreo biomédico IoT.

---

## 🎯 Visión General

### Stack Tecnológico

**Hardware:**
- Raspberry Pi 5 (4GB RAM)
- MLX90640ESF-BAB (Cámara térmica 24×32)
- MAX30102 (SpO2 y frecuencia cardíaca)
- MPX5050 + ADS1115 (Presión arterial oscilométrica)

**Backend:**
- Python 3.13 (Edge processing)
- PyQt6 (Interfaz local)
- FastAPI (REST API)
- SQLite (Persistencia)
- Mosquitto (MQTT Broker)

**Frontend:**
- Next.js 14 (PWA)
- React 18 + TypeScript
- TailwindCSS

---

## 🏛️ Arquitectura del Sistema

### Diagrama de Componentes
┌─────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 5                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Edge Processing (PyQt6)                 │  │
│  │                                                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │ MLX90640   │  │ MAX30102   │  │ MPX5050    │    │  │
│  │  │ Thermal    │  │ SpO2/HR    │  │ BP         │    │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘    │  │
│  │        │                │                │           │  │
│  │        └────────────────┴────────────────┘           │  │
│  │                         │                            │  │
│  │                         ▼                            │  │
│  │         ┌───────────────────────────────┐           │  │
│  │         │   Processing Layer            │           │  │
│  │         │   • temperature.py            │           │  │
│  │         │   • spo2_monitor.py           │           │  │
│  │         │   • pressure.py               │           │  │
│  │         └───────────┬───────────────────┘           │  │
│  │                     │                                │  │
│  │                     ▼                                │  │
│  │         ┌───────────────────────────────┐           │  │
│  │         │   Session Manager             │           │  │
│  │         │   • on_spo2_stable()          │           │  │
│  │         │   • on_bp_result()            │           │  │
│  │         │   • on_temp_reading()         │           │  │
│  │         └───────────┬───────────────────┘           │  │
│  │                     │                                │  │
│  │                     │ guarda                         │  │
│  │                     ▼                                │  │
│  │         ┌───────────────────────────────┐           │  │
│  │         │      biomed.db (local)        │           │  │
│  │         │  • spo2_measurements          │           │  │
│  │         │  • spo2_raw                   │           │  │
│  │         │  • bp_measurements            │           │  │
│  │         │  • bp_raw                     │           │  │
│  │         │  • temp_measurements          │           │  │
│  │         └───────────┬───────────────────┘           │  │
│  │                     │                                │  │
│  │                     │ lee y publica                  │  │
│  │                     ▼                                │  │
│  │         ┌───────────────────────────────┐           │  │
│  │         │    MQTT Publisher             │           │  │
│  │         │  • publish_spo2()             │           │  │
│  │         │  • publish_bp()               │           │  │
│  │         │  • publish_temp()             │           │  │
│  │         └───────────┬───────────────────┘           │  │
│  └─────────────────────┼──────────────────────────────┘  │
│                        │                                  │
│                        │ publica                          │
│                        ▼                                  │
│            ┌───────────────────────────┐                 │
│            │   MQTT Broker             │                 │
│            │   (Mosquitto)             │                 │
│            │                           │                 │
│            │   Topics:                 │                 │
│            │   • biomed/pi5-001/temp   │                 │
│            │   • biomed/pi5-001/spo2   │                 │
│            │   • biomed/pi5-001/bp     │                 │
│            │   • biomed/pi5-001/       │                 │
│            │     session/end           │                 │
│            └───────────┬───────────────┘                 │
│                        │                                  │
│                        │ subscribe                        │
│                        ▼                                  │
│            ┌───────────────────────────┐                 │
│            │   MQTT Subscriber         │                 │
│            │   • on_message()          │                 │
│            │   • Replica a storage.db  │                 │
│            └───────────┬───────────────┘                 │
│                        │                                  │
│                        │ escribe                          │
│                        ▼                                  │
│            ┌───────────────────────────┐                 │
│            │   storage.db              │                 │
│            │   (permanente)            │                 │
│            │   • Mismas tablas que     │                 │
│            │     biomed.db             │                 │
│            └───────────┬───────────────┘                 │
│                        │                                  │
│                        │ lee                              │
│                        ▼                                  │
│            ┌───────────────────────────┐                 │
│            │   FastAPI REST API        │                 │
│            │   (puerto 8000)           │                 │
│            │   • /sessions             │                 │
│            │   • /measurements/*       │                 │
│            │   • /raw/*                │                 │
│            └───────────┬───────────────┘                 │
└────────────────────────┼──────────────────────────────────┘
│
│ HTTP/HTTPS
▼
┌────────────────────┐
│   Next.js PWA      │
│   (puerto 3000)    │
│                    │
│   Celular / PC     │
└────────────────────┘

### Flujo de Datos Completo

Sensores físicos (MLX90640, MAX30102, MPX5050)
↓
Processing Layer (temperature.py, spo2_monitor.py, pressure.py)
↓
Session Manager (coordina guardado y publicación)
↓
biomed.db ← Guarda datos procesados + raw (synced=1)
↓
MQTT Publisher ← Lee de biomed.db y publica
↓
MQTT Broker ← Distribuye mensajes
↓
MQTT Subscriber ← Recibe mensajes
↓
storage.db ← Replica datos (permanente)
↓
FastAPI ← Lee SOLO de storage.db
↓
PWA ← Consume API vía HTTP/HTTPS


**Puntos clave:**
- ✅ `biomed.db` → MQTT Publisher → MQTT Broker
- ✅ `storage.db` → FastAPI (NO hay conexión con biomed.db)
- ✅ Todo pasa por MQTT (no hay copia directa entre DBs)

---

## 🔄 Flujo de Datos Detallado

### 1. Captura de Datos (Edge)

```python
# Ejemplo: SpO2
monitor = SpO2Monitor()  # Lee MAX30102
spo2, hr = monitor.spo2, monitor.bpm
ir_buf = monitor.ir_buffer
red_buf = monitor.red_buffer

# SessionManager guarda en biomed.db
spo2_id = save_spo2(
    session_id, spo2, hr,
    ir_buf, red_buf, thresh_high, thresh_low
)

# DESPUÉS publica a MQTT (lee de biomed.db o usa valores en memoria)
mqtt.publish_spo2(
    spo2_id=spo2_id,
    spo2=spo2,
    hr=hr,
    session_id=session_id,
    ir_buf=ir_buf,        # ← Raw incluido
    red_buf=red_buf,      # ← Raw incluido
    thresh_high=thresh_high,
    thresh_low=thresh_low
)
```

### 2. Payload MQTT

```json
{
  "device_id": "pi5-001",
  "session_id": 42,
  "spo2_id": 123,
  "ts": 1715123456.789,
  "spo2": 96.5,
  "hr": 72,
  "raw": {
    "ir_json": "[100, 102, 104, ...]",
    "red_json": "[200, 205, 210, ...]",
    "thresh_high_json": "[110, 112, ...]",
    "thresh_low_json": "[90, 88, ...]",
    "sample_rate_hz": 25.0
  }
}
```

### 3. Subscriber Replica

```python
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)
    
    # Guardar en storage.db
    conn = sqlite3.connect('data/storage.db')
    
    # Medición procesada
    conn.execute(
        "INSERT INTO spo2_measurements (...) VALUES (...)",
        (payload['spo2_id'], payload['spo2'], payload['hr'], ...)
    )
    
    # Raw (si existe)
    if 'raw' in payload:
        conn.execute(
            "INSERT INTO spo2_raw (...) VALUES (...)",
            (payload['spo2_id'], payload['raw']['ir_json'], ...)
        )
    
    conn.commit()
```

### 4. FastAPI Lee storage.db

```python
@app.get("/measurements/spo2")
def get_spo2(session_id: int):
    # Lee SOLO de storage.db
    conn = sqlite3.connect("data/storage.db")
    rows = conn.execute(
        "SELECT * FROM spo2_measurements WHERE session_id = ?",
        (session_id,)
    ).fetchall()
    return [dict(r) for r in rows]
```

---

## 🗄️ Bases de Datos

### biomed.db (Local - Edge)

**Propósito:** 
- Almacenamiento local rápido
- Fuente para publicación MQTT

**Escritura:** Edge (Session Manager)  
**Lectura:** Edge + MQTT Publisher  

### storage.db (Permanente - API)

**Propósito:**
- Base de datos permanente
- Fuente de verdad para API/PWA

**Escritura:** MQTT Subscriber  
**Lectura:** FastAPI  

**IMPORTANTE:** No hay conexión directa entre estas DBs.

---

## 📡 MQTT Architecture

### Topics
biomed/pi5-001/temp         ← Temperatura corporal
biomed/pi5-001/spo2         ← SpO2 + HR + raw (IR, Red, umbrales)
biomed/pi5-001/bp           ← Presión arterial + raw (señales completas)
biomed/pi5-001/session/end  ← Cierre de sesión

### Características

- **QoS 1:** Garantía de entrega (al menos una vez)
- **Payload JSON:** Datos procesados + raw en un solo mensaje
- **Store-and-forward:** Si MQTT falla, queda en biomed.db para reintentar
- **Sin duplicados:** Una publicación por medición

---

## ⚙️ Servicios Systemd

### 4 Servicios Activos

| Servicio | Función | Puerto |
|----------|---------|--------|
| biomed-edge | Edge UI + lectura sensores | Display |
| biomed-mqtt-subscriber | Replica MQTT → storage.db | - |
| biomed-fastapi | API REST | 8000 |
| biomed-pwa | PWA producción HTTPS | 3000 |

### Gestión con Script Helper

```bash
# Modo interactivo (menú visual)
./biomed-control.sh

# Comandos directos
./biomed-control.sh start
./biomed-control.sh enable
./biomed-control.sh status
./biomed-control.sh logs edge
```

---

## 🧮 Algoritmos de Procesamiento

### Temperatura (MLX90640)

**Detección dinámica de persona:**
```python
# Umbral relativo al ambiente
ambient = np.percentile(frame, 10)
threshold = ambient + 5.0  # Margen configurable

# Detectar regiones calientes
mask = frame > threshold
if mask.any():
    # P95 de la región detectada
    temp_body = np.percentile(frame[mask], 95)
```

### SpO2 (MAX30102)

**Procesamiento de señal:**
```python
# Filtro pasa-banda (0.5-5 Hz)
ir_filtered = bandpass_filter(ir_raw, fs=25)

# Detección de picos
peaks = find_peaks(ir_filtered, distance=fs*0.4)
hr = 60 / np.mean(np.diff(peaks) / fs)

# Cálculo SpO2
R = (ac_red/dc_red) / (ac_ir/dc_ir)
spo2 = 110 - 25*R  # Fórmula empírica
```

### Presión Arterial (Oscilométrico)

**Eliminación de transitorio:**
```python
# 1. Encontrar pico máximo de presión (fin de inflado)
idx_max_presion = np.argmax(p_picos)

# 2. Descartar primeros 3 picos (zona transitorio)
idx_inicio_valido = idx_max_presion + 3
picos_validos = picos[idx_inicio_valido:]
p_valida = p_picos[idx_inicio_valido:]

# 3. Calcular envolvente sobre zona limpia
envolvente = savgol_filter(amplitudes_validas)

# 4. MAP = máximo de envolvente
idx_map = np.argmax(envolvente)
map_mmhg = p_valida[idx_map]

# 5. SYS y DIA por ratios
sys_mmhg = calcular_por_ratio(envolvente, 0.55, hacia_arriba)
dia_mmhg = calcular_por_ratio(envolvente, 0.75, hacia_abajo)
```

---

## 🌐 API REST

**Base URL:** `http://harlink.local:8000`

### Endpoints Principales
GET /health
GET /sessions
GET /sessions/{session_id}
GET /measurements/temp?session_id={id}
GET /measurements/spo2?session_id={id}
GET /measurements/bp?session_id={id}
GET /raw/spo2/{measurement_id}
GET /raw/bp/{measurement_id}
GET /patient/summary

### Ejemplo de Respuesta

```json
{
  "id": 123,
  "session_id": 42,
  "ts": 1715123456.789,
  "spo2_pct": 96.5,
  "hr_bpm": 72
}
```

---

## 💻 PWA Frontend

**Stack:**
- Next.js 14 (App Router)
- React 18 + TypeScript
- TailwindCSS
- Recharts (gráficas)
- Canvas (señales raw)

**Características:**
- Instalable en celular/PC
- Modo offline (Service Worker)
- HTTPS (self-signed cert)
- Actualización en tiempo real

---

**Versión:** 4.0  
**Última actualización:** Mayo 2026  
**Autor:** Luis Raul (harlink)
