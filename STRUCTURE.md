# Estructura del Proyecto biomed-pi5

Sistema IoT de monitoreo biomédico en Raspberry Pi 5 con sensores MLX90640 (temperatura), MAX30102 (SpO2), y MPX5050 (presión arterial).

## Arquitectura General
┌─────────────────────────────────────────────────────────────────┐
│                        RASPBERRY PI 5                            │
│                                                                  │
│  ┌────────────────────┐         ┌──────────────────────┐       │
│  │   Edge (PyQt6)     │────────▶│  Mosquitto Broker    │       │
│  │   - Lee sensores   │         │  localhost:1883      │       │
│  │   - Guarda local   │         └──────────┬───────────┘       │
│  │   - Publica MQTT   │                    │                    │
│  └─────────┬──────────┘                    │                    │
│            │                                │                    │
│            ▼                                ▼                    │
│     biomed.db ◀──────────────┐    ┌─────────────────┐          │
│     (local)                   │    │ MQTT Subscriber │          │
│                               │    │ + Raw Sync      │          │
│                               │    └────────┬────────┘          │
│                               │             │                    │
│                               │             ▼                    │
│                               │      storage.db                  │
│                               │      (permanente)                │
│                               │             │                    │
│                               │             ▼                    │
│  ┌────────────────────────────┼──────FastAPI────────┐          │
│  │                            │    (puerto 8000)     │          │
│  │  Datos procesados ◀────────┘                     │          │
│  │  + señales raw                                    │          │
│  └───────────────────────────────────────┬──────────┘          │
│                                           │                      │
└───────────────────────────────────────────┼──────────────────────┘
│
▼
┌──────────────────────────┐
│   Next.js PWA (HTTPS)    │
│   puerto 3000            │
│   - 5 páginas            │
│   - Instalable           │
│   - Waveform viewer      │
└──────────────────────────┘## Estructura de Directorios
## Estructura de Directorios
biomed-pi5/
│
├── config/                      # Configuración del sistema
│   ├── settings.yaml            # Configuración sensores, MQTT, storage
│   └── patient.json             # Datos del paciente actual
│
├── core/                        # Núcleo del sistema
│   ├── logger.py                # Sistema de logging
│   └── manager.py               # Orquestador principal
│
├── data/                        # Bases de datos SQLite
│   ├── biomed.db                # DB local (Edge) - store-and-forward
│   └── storage.db               # DB permanente (API/PWA)
│
├── drivers/                     # Drivers de hardware
│   ├── mlx90640.py              # Sensor térmico MLX90640 (24×32 IR matrix)
│   ├── max30102.py              # Sensor SpO2/HR MAX30102
│   └── ads1115.py               # ADC para sensor de presión MPX5050
│
├── processing/                  # Algoritmos de procesamiento
│   ├── temperature.py           # Procesamiento térmico
│   │   ├── get_body_temperature()    # Extrae temp corporal P95
│   │   ├── classify_temperature()    # Clasifica estado térmico
│   │   └── get_scene_stats()         # Estadísticas de escena
│   ├── spo2_monitor.py          # Monitor SpO2 en tiempo real
│   │   ├── Filtrado AC/DC
│   │   ├── Cálculo R-ratio
│   │   ├── Detección de peaks
│   │   └── Validación de señal
│   └── bp_monitor.py            # Monitor presión arterial
│       ├── Oscilometric method
│       ├── Envelope detection
│       ├── Peak analysis
│       └── MAP/SYS/DIA calculation
│
├── storage/                     # Capa de persistencia
│   ├── db.py                    # Operaciones SQLite base
│   ├── session_manager.py       # Gestión de sesiones
│   │   ├── Store-and-forward MQTT
│   │   ├── Timers de guardado
│   │   └── Validación de mediciones
│   └── mqtt_publisher.py        # Publicador MQTT
│       ├── Publica temp/spo2/bp
│       ├── Incluye datos raw opcionales
│       └── QoS=1 (at least once)
│
├── ui/                          # Interfaz PyQt6
│   ├── main_window.py           # Ventana principal con tabs
│   ├── colors.py                # Paleta de colores
│   ├── components/              # Componentes reutilizables
│   │   ├── toast.py             # Notificaciones toast
│   │   ├── card.py              # Tarjetas de datos
│   │   ├── badge.py             # Badges de estado
│   │   └── dialog.py            # Diálogos (bienvenida, paciente)
│   └── widgets/                 # Páginas/Widgets principales
│       ├── thermal_widget2.py   # Tab temperatura (MLX90640)
│       ├── spo2_widget2.py      # Tab SpO2 (MAX30102)
│       ├── pressure_widget2.py  # Tab presión arterial
│       └── patient_widget.py    # Tab datos del paciente
│
├── services/                    # Servicios backend
│   ├── mqtt_subscriber.py       # Replica MQTT → storage.db
│   │   ├── Escucha temp/spo2/bp
│   │   ├── Soporta formato viejo y nuevo
│   │   ├── Guarda datos procesados
│   │   └── Guarda datos raw (señales)
│   │
│   ├── raw_sync_service.py      # Sincroniza raw con synced=0
│   │   ├── Lee biomed.db cada 30s
│   │   ├── Publica raw vía MQTT
│   │   └── Marca synced=1 al publicar
│   │
│   ├── storage/                 # FastAPI REST API
│   │   ├── main.py              # Servidor FastAPI
│   │   ├── models.py            # Modelos Pydantic
│   │   ├── crud.py              # Operaciones CRUD
│   │   └── endpoints/           # Endpoints organizados
│   │       ├── patient.py       # /patient/* (8 endpoints)
│   │       ├── doctor.py        # /doctor/* (10 endpoints)
│   │       └── admin.py         # /admin/* (6 endpoints)
│   │
│   └── webapp/                  # Next.js PWA
│       ├── app/                 # App Router (Next.js 14)
│       │   ├── page.tsx         # Inicio
│       │   ├── layout.tsx       # Layout global
│       │   └── globals.css      # Estilos globales
│       ├── components/
│       │   ├── Sidebar.tsx      # Navegación lateral
│       │   ├── ThemeToggle.tsx  # Toggle claro/oscuro
│       │   ├── WaveformViewer.tsx  # Viewer señales raw
│       │   └── pages/           # Páginas principales
│       │       ├── PageHome.tsx      # Inicio - resumen
│       │       ├── PageMediciones.tsx # Historial mediciones
│       │       ├── PagePaciente.tsx  # Info del paciente
│       │       ├── PageDoctor.tsx    # Vista médico
│       │       └── PageAjustes.tsx   # Configuración
│       ├── lib/
│       │   └── api.ts           # Cliente API FastAPI
│       ├── public/
│       │   ├── manifest.json    # PWA manifest
│       │   └── icons/           # Iconos PWA
│       ├── next.config.ts       # Config Next.js
│       ├── start-https.mjs      # Servidor HTTPS dev
│       ├── package.json
│       └── tsconfig.json
│
├── tools/                       # Utilidades (futuro)
│   └── dataset_collector.py    # Colector de datasets térmicos
│
├── tests/                       # Tests (futuro)
│   ├── test_drivers.py
│   ├── test_processing.py
│   └── mocks/
│
├── main.py                      # Entry point Edge
├── requirements.txt             # Dependencias Python
├── STRUCTURE.md                 # Este archivo
└── README.md                    # Documentación principal
## Base de Datos

### biomed.db (Edge - Local)
```sql
sessions                  -- Sesiones de monitoreo
├── id (PK)
├── patient_id
├── started_at
├── ended_at
├── device_id
└── synced               -- 0=pendiente, 1=sincronizado

temp_measurements         -- Mediciones de temperatura
├── id (PK)
├── session_id (FK)
├── ts
├── temp_c
├── state
├── max_c, min_c, ambient_c
└── synced

spo2_measurements         -- Mediciones SpO2
├── id (PK)
├── session_id (FK)
├── ts
├── spo2_pct
├── hr_bpm
└── synced

spo2_raw                  -- Señales raw SpO2
├── id (PK)
├── spo2_measurement_id (FK)
├── ir_json              -- Buffer infrarrojo
├── red_json             -- Buffer rojo
├── thresh_high_json     -- Umbral alto
├── thresh_low_json      -- Umbral bajo
├── sample_rate_hz
└── synced

bp_measurements           -- Mediciones presión arterial
├── id (PK)
├── session_id (FK)
├── ts
├── sys_mmhg, dia_mmhg, map_mmhg
├── hr_bpm
├── category
└── synced

bp_raw                    -- Señales raw presión
├── id (PK)
├── bp_measurement_id (FK)
├── pressure_json        -- Señal de presión
├── time_json            -- Timestamps
├── osc_json             -- Oscilaciones
├── peaks_json           -- Picos detectados
├── env_json             -- Envolvente
├── fs_hz                -- Sample rate
└── synced
```

### storage.db (API - Permanente)
Mismo schema que `biomed.db` pero **synced siempre=1** (datos replicados vía MQTT).

## Flujo de Datos

### 1. Temperatura (continuo)
MLX90640 → thermal_widget2.py → SessionManager
↓ cada 10s estable
biomed.db temp_measurements
↓ MQTT publish
Mosquitto → Subscriber → storage.db
### 2. SpO2 (cada 90s)
MAX30102 → spo2_widget2.py → SpO2Monitor
↓ validación señal
SessionManager (timer 90s)
↓ guarda procesado + raw
biomed.db: spo2_measurements + spo2_raw
↓ MQTT publish (incluye raw)
Mosquitto → Subscriber → storage.db (ambas tablas)
↓ si falla
raw_sync_service reintenta cada 30s
### 3. Presión Arterial (bajo demanda)
MPX5050 + ADS1115 → pressure_widget2.py → BPMonitor
↓ medición completa (~30s)
SessionManager
↓ guarda procesado + raw
biomed.db: bp_measurements + bp_raw
↓ MQTT publish (incluye raw)
Mosquitto → Subscriber → storage.db (ambas tablas)
↓ si falla
raw_sync_service reintenta cada 30s

## MQTT Topics
biomed/pi5-001/temp
Payload: {device_id, session_id, temp_id, ts, temp_c, state, max_c, min_c, ambient_c}
biomed/pi5-001/spo2
Payload: {device_id, session_id, spo2_id, ts, spo2, hr}
Payload con raw: {..., raw: {ir_json, red_json, thresh_high_json, thresh_low_json, sample_rate_hz}}
biomed/pi5-001/bp
Payload: {device_id, session_id, bp_id, ts, sys, dia, map, hr, category}
Payload con raw: {..., raw: {pressure_json, time_json, osc_json, peaks_json, env_json, fs_hz}}
## FastAPI Endpoints (24 total)

### Patient Endpoints (8)
- GET `/patient/summary` - Resumen del paciente actual
- GET `/patient/latest` - Últimas mediciones
- GET `/patient/history` - Historial de mediciones
- GET `/patient/sessions` - Sesiones del paciente
- GET `/patient/vitals` - Signos vitales actuales
- GET `/patient/trends` - Tendencias temporales
- GET `/patient/alerts` - Alertas activas
- GET `/patient/export` - Exportar datos

### Doctor Endpoints (10)
- GET `/doctor/patients` - Lista de pacientes
- GET `/doctor/patient/{id}` - Detalles de paciente
- GET `/doctor/sessions` - Todas las sesiones
- GET `/doctor/sessions/{id}` - Detalles de sesión
- GET `/doctor/sessions/{id}/waveform/spo2/{mid}` - Señal SpO2 raw
- GET `/doctor/sessions/{id}/waveform/bp/{mid}` - Señal BP raw
- GET `/doctor/analytics` - Analytics generales
- GET `/doctor/reports` - Reportes médicos
- POST `/doctor/notes` - Agregar nota médica
- GET `/doctor/search` - Búsqueda avanzada

### Admin Endpoints (6)
- GET `/admin/stats` - Estadísticas del sistema
- GET `/admin/devices` - Dispositivos conectados
- GET `/admin/logs` - Logs del sistema
- POST `/admin/calibrate` - Calibrar sensores
- GET `/admin/mqtt/status` - Estado MQTT
- POST `/admin/sync` - Forzar sincronización

## PWA Páginas

1. **Inicio** - Dashboard con últimas mediciones y alertas
2. **Mediciones** - Historial completo con filtros
3. **Paciente** - Información del paciente y configuración
4. **Doctor** - Vista médico con waveforms y análisis
5. **Ajustes** - Configuración de la aplicación

## Tecnologías

### Hardware
- Raspberry Pi 5 (headless)
- MLX90640 (I2C 0x33) - Sensor térmico 24×32
- MAX30102 (I2C 0x57) - Sensor SpO2/HR
- ADS1115 (I2C 0x48) - ADC 16-bit
- MPX5050 - Sensor presión 0-50 kPa

### Software
- Python 3.13
- PyQt6 (UI Edge)
- FastAPI (REST API)
- Next.js 14 (PWA)
- SQLite (persistencia)
- Mosquitto (MQTT broker)
- paho-mqtt (MQTT client)
- Tailwind CSS (estilos PWA)

## Decisiones de Diseño

1. **Dos DBs separadas**: `biomed.db` (edge rápido) vs `storage.db` (API/PWA)
2. **MQTT store-and-forward**: Datos procesados se reintentan si falla publicación
3. **Raw sync service**: Servicio separado para señales raw (no bloquea Edge)
4. **QoS=1**: Garantiza entrega "al menos una vez" (puede duplicar)
5. **Dynamic thresholding**: Temperatura relativa a ambiente (no rangos fijos)
6. **Calibration offset**: 0.7°C para temperatura frontal vs oral
7. **mDNS**: `harlink.local` para portabilidad entre redes
8. **HTTPS dev**: Certificado local para PWA instalable

## Roadmap Futuro

- [ ] Systemd services para arranque automático
- [ ] Dataset térmico para ML (detección facial opcional)
- [ ] Export a CSV/PDF
- [ ] Gráficas interactivas con zoom/pan
- [ ] Nginx reverse proxy
- [ ] Modo producción Next.js
- [ ] Alerts en tiempo real (websockets)
- [ ] Multi-paciente en PWA
