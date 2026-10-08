# 🩺 BioMed Pi5 — Guía de Uso Rápido

Sistema IoT de monitoreo biomédico con arquitectura MQTT para replicación de datos en tiempo real.

---

## 🚀 Instalación desde Cero (Git Clone)

Si restauras el proyecto desde GitHub o lo instalas en una Pi nueva, ejecuta **un solo script** que configura todo:

```bash
git clone https://github.com/RaulH96/biomed-pi5
cd biomed-pi5
bash setup.sh
```

### Qué hace `setup.sh`

| Paso | Acción |
|------|--------|
| 1 | Instala paquetes del sistema (libgpiod, Qt6, i2c-tools…) |
| 2 | Instala y activa **Mosquitto** MQTT broker |
| 3 | Instala **Node.js + npm** |
| 4 | Habilita **I2C y SPI** (sensores MLX90640, MAX30102, MPX5050) |
| 5 | Configura hostname `harlink` + **avahi** → `harlink.local` sin depender de IP |
| 6 | Crea `.venv` e instala **requirements.txt** con las versiones fijadas en `requirements.lock` |
| 7 | `npm ci` en `services/webapp/`, genera el certificado SSL y **compila la PWA** (`npm run build`) |
| 8 | Crea directorios `assets/` y `data/`, genera **accesos directos** en el escritorio |
| 9 | Instala los **servicios** y deja el **arranque automático habilitado**; arranca todo y lo verifica |

Al terminar **todo queda corriendo** y vuelve a arrancar solo cada vez que se enciende la Pi. Solo pregunta si deseas reiniciar cuando hace falta (I2C/SPI recién activados o hostname nuevo).

> **Importante:** ejecuta `bash setup.sh` **sin** `sudo` (el script pide la contraseña cuando la necesita). El usuario debe ser `harlink`.

> **Nota:** `node_modules/`, `.venv/` y `.next/` están en `.gitignore` y no se guardan en el repo. `setup.sh` los reconstruye en cada instalación nueva. Las bases de datos de `data/`, `config/patient.json` y las fotos de `assets/` **sí** están en el repo: son los datos de demo.

---

## 🔧 Recuperar el Entorno Python (.venv)

Si el entorno virtual se corrompe o se pierde sin necesidad de reinstalar todo el sistema:

```bash
cd /home/harlink/biomed-pi5
bash recover_venv.sh
```

### Qué hace `recover_venv.sh`

1. Verifica que `requirements.txt` exista en el proyecto (no lo sobreescribe)
2. Instala dependencias del sistema necesarias para compilar paquetes nativos
3. Elimina el `.venv` roto y crea uno nuevo con `--system-site-packages`
4. Instala todos los paquetes del `requirements.txt` completo (FastAPI, uvicorn, paho-mqtt, PyQt6, Adafruit…)
5. Verifica importaciones críticas y reporta el resultado

> **Diferencia con `setup.sh`:** `recover_venv.sh` solo recrea el venv Python. No toca Node.js, Mosquitto, hostname ni hardware. Más rápido para recuperar solo el entorno.

---

## 🎯 Inicio Rápido

### Opción 1: Script Helper Interactivo (Recomendado)

```bash
cd /home/harlink/biomed-pi5
./biomed-control.sh
```

Se abrirá un menú interactivo con todas las opciones:
```
🩺 Biomed Pi5 - Control de Servicios
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] ▶  Iniciar todos los servicios
[2] ◼  Detener todos los servicios
[3] ⟳  Reiniciar todos los servicios
[4] ℹ  Ver estado de servicios
[5] ✓  Habilitar inicio automático (boot)
[6] ✗  Deshabilitar inicio automático
[7] ?  Verificar configuración de arranque
[8] 📋 Ver logs en tiempo real
[9] 🔧 Reinstalar servicios
[10] 🧹 Limpiar logs antiguos
[11] 🏗  Recompilar PWA (tras editar la webapp)
[0] Salir
```

Ninguna opción pide contraseña: los servicios son servicios systemd **de usuario**.

### Opción 2: Comandos Directos

```bash
# Iniciar servicios
./biomed-control.sh start

# Habilitar auto-arranque
./biomed-control.sh enable

# Ver estado
./biomed-control.sh status
```

### Opción 3: Íconos del Escritorio

**Doble click en:**
- 💚 **Biomed Pi5 (DESARROLLO)** → Detiene los servicios de producción y abre los 4 componentes en terminales, con hot reload (PWA en `http://harlink.local:3000`)
- 🚀 **Biomed Pi5 (PRODUCCIÓN)** → (Re)inicia los servicios de producción (PWA HTTPS compilada, instalable) y muestra su estado

> Los accesos directos se crean automáticamente al ejecutar `setup.sh`. Si no aparecen, vuelve a ejecutarlo.

---

## 🔧 Script Helper - biomed-control.sh

Herramienta todo-en-uno para gestionar los servicios del sistema.

### Modo Interactivo (Sin Argumentos)

```bash
./biomed-control.sh
```

Abre un menú visual donde puedes:
- Iniciar/detener/reiniciar servicios
- Habilitar/deshabilitar auto-arranque
- Ver logs en tiempo real
- Reinstalar servicios si algo falla

### Modo Comando (Con Argumentos)

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

`setup.sh` lo deja **habilitado** por defecto.

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
./biomed-control.sh logs edge
./biomed-control.sh logs mqtt-subscriber
./biomed-control.sh logs fastapi
./biomed-control.sh logs pwa
```

**Reinstalar servicios** (si algo crashea o moviste el proyecto de carpeta):
```bash
./biomed-control.sh reinstall
```

**Recompilar la PWA** (después de editar `services/webapp/`; producción usa la versión compilada):
```bash
./biomed-control.sh build
```

**Limpiar logs antiguos:**
```bash
./biomed-control.sh clean
```

---

## 🏗️ Servicios del Sistema

El sistema está compuesto por 4 componentes independientes:

| Componente | Descripción | Puerto | Cómo arranca |
|----------|-------------|--------|--------------|
| **biomed-edge** | Interfaz PyQt6, lee sensores físicos | Pantalla | Autoarranque del escritorio (`~/.config/autostart/biomed-edge.desktop`) |
| **biomed-mqtt-subscriber** | Replica datos procesados → storage.db | - | Servicio systemd de usuario |
| **biomed-fastapi** | API REST para PWA | 8000 | Servicio systemd de usuario |
| **biomed-pwa** | PWA compilada, producción (HTTPS) | 3000 | Servicio systemd de usuario |

- Los 3 servicios son **de usuario** (`~/.config/systemd/user/`): se controlan sin `sudo` (`systemctl --user status biomed-pwa`). Con *linger* activo (lo configura `setup.sh`) arrancan al encender la Pi, aunque nadie inicie sesión, y se reinician solos si fallan.
- La Edge UI necesita el escritorio (Wayland), por eso se abre con el autoarranque del escritorio y no como servicio.
- La PWA consume la API a través de su propio servidor (`/backend/...` → `127.0.0.1:8000`), así que funciona por `harlink.local` o por IP, por HTTP o HTTPS, sin configurar nada.

### Flujo de datos

```
Edge → lee sensores → guarda biomed.db → publica MQTT
                                                    ↓
                               Mosquitto distribuye mensajes
                                                    ↓
                          Subscriber recibe → guarda storage.db
                                                    ↓
                                   FastAPI expone REST API
                                                    ↓
                                       PWA muestra al usuario
```

---

## 📱 Acceso desde Otros Dispositivos

### URLs de Acceso

| Servicio | URL | Cuándo usar |
|----------|-----|-------------|
| PWA Prod | https://harlink.local:3000 (o `https://<IP>:3000`) | Modo producción (instalable) |
| PWA Dev | http://harlink.local:3000 | Desarrollo con hot reload |
| API Docs | http://harlink.local:8000/docs | Swagger UI interactivo |
| API Health | http://harlink.local:8000/health | Verificar funcionamiento |

> `harlink.local` funciona en cualquier red gracias a avahi-daemon (mDNS). No depende de IP fija.

### Instalar PWA en Celular

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

No hay que hacer nada: después de `setup.sh` todo arranca solo al encender la Pi.
PWA instalable: https://harlink.local:3000

Si lo deshabilitaste para programar, vuelve a dejarlo listo con:
```bash
./biomed-control.sh enable   # opción [5] en menú interactivo
```

### Para Desarrollo / Programación

**Rápido:** doble click en **Biomed Pi5 (DESARROLLO)**. Detiene los servicios de producción y abre los 4 componentes con hot reload (PWA en `http://harlink.local:3000`). Para volver: ícono **PRODUCCIÓN** o reiniciar la Pi.

**Sesión larga** (que no arranque producción al reiniciar):
```bash
./biomed-control.sh disable   # opción [6]
./biomed-control.sh stop
cd services/webapp && npm run dev
```

Al terminar, si cambiaste la webapp: `./biomed-control.sh build` y luego `./biomed-control.sh enable`.

---

## 💾 Cierre de Sesión

Las sesiones se cierran de 2 formas:

### 1️⃣ Botón Manual (en Edge UI)

1. Ve al tab **Paciente** (👤)
2. Click en **"🔒 Cerrar Sesión"**
3. Aparece el diálogo de bienvenida para iniciar una nueva sesión
4. Elige: continuar con el mismo paciente, cambiar paciente, o sesión anónima

### 2️⃣ Al Cerrar Edge

Al cerrar la ventana (X o Alt+F4), se cierra la sesión activa automáticamente y se replica a `storage.db` vía MQTT.

---

## 🗄️ Bases de Datos

### biomed.db (Edge - Local)
- **Ubicación:** `data/biomed.db`
- **Función:** Almacenamiento local rápido del Edge

### storage.db (API - Permanente)
- **Ubicación:** `data/storage.db`
- **Función:** Datos replicados vía MQTT, consumidos por FastAPI/PWA

### Datos de Demo

Las dos bases del repo traen datos **sintéticos** de demo: ~35 sesiones de los últimos 30 días para la paciente de `config/patient.json` (hipertensión tratada: la presión mejora a lo largo del mes, con un episodio de febrícula), con señales crudas fisiológicas (PPG de SpO2 y oscilometría de presión) coherentes con los valores guardados.

Para regenerarlas (por ejemplo, para que las gráficas de 7 días vuelvan a quedar al día):
```bash
./biomed-control.sh stop
.venv/bin/python tools/generar_demo.py            # opciones: --dias 45 --semilla 3
./biomed-control.sh start
```

> Reemplaza `biomed.db` y `storage.db` por completo: las sesiones medidas de verdad se pierden (respáldalas antes si las quieres).

### Ver Datos

```bash
# Últimas mediciones de SpO2
sqlite3 data/biomed.db "SELECT id, ts, spo2_pct, hr_bpm FROM spo2_measurements ORDER BY id DESC LIMIT 5"

# Ver sesiones abiertas
sqlite3 data/storage.db "SELECT id, started_at, ended_at FROM sessions WHERE ended_at IS NULL"
```

---

## 🔌 MQTT

### Topics
```
biomed/pi5-001/temp         ← Temperatura corporal
biomed/pi5-001/spo2         ← SpO2 + HR (con señales raw IR/Red)
biomed/pi5-001/bp           ← Presión arterial (con señales raw)
biomed/pi5-001/session/end  ← Cierre de sesión
```

### Monitorear Mensajes

```bash
# Ver todos los mensajes en tiempo real
mosquitto_sub -h localhost -t 'biomed/pi5-001/#' -v
```

---

## 🌐 Red — harlink.local

El hostname `harlink.local` funciona en **cualquier red** sin reconfigurar gracias a avahi-daemon (mDNS).

```bash
# Verificar avahi
sudo systemctl status avahi-daemon

# Si no está activo
sudo systemctl enable avahi-daemon && sudo systemctl start avahi-daemon

# Ver IP actual (alternativa si mDNS no funciona)
hostname -I
```

---

## 🐛 Troubleshooting

### Entorno Python roto
```bash
bash recover_venv.sh
```

### Node.js / webapp no arranca
```bash
cd services/webapp && npm ci && cd ../..
./biomed-control.sh build          # recompila y reinicia la PWA
```

### Mosquitto no corre
```bash
sudo systemctl enable mosquitto && sudo systemctl start mosquitto
```

### Sensores I2C no detectados
```bash
sudo raspi-config nonint do_i2c 0 && sudo reboot
# Verificar después del reinicio:
i2cdetect -y 1
```

### Servicios no arrancan
```bash
./biomed-control.sh status         # qué está activo
./biomed-control.sh logs fastapi   # ver error (edge | mqtt-subscriber | fastapi | pwa)
./biomed-control.sh reinstall      # reinstalar servicios
```

### Edge no aparece en pantalla
```bash
./biomed-control.sh edge-start     # abrirla en el escritorio actual
./biomed-control.sh logs edge      # ver error (logs/edge.log)
ls ~/.config/autostart/biomed-edge.desktop   # autoarranque presente
```

### PWA no carga / sin datos
```bash
./biomed-control.sh status         # prueba PWA + API de punta a punta
ls services/webapp/*.pem           # verificar certificados SSL
./biomed-control.sh logs pwa
./biomed-control.sh build          # recompilar si cambiaste la webapp
```

### Sesiones "En curso" huérfanas
```bash
sqlite3 data/storage.db "SELECT id, started_at FROM sessions WHERE ended_at IS NULL"
# Cerrar desde Edge UI: tab Paciente → "Cerrar Sesión"
```

---

## 📁 Estructura del Proyecto

```
biomed-pi5/
├── setup.sh                 # ← Setup completo desde cero (post git clone)
├── recover_venv.sh          # ← Recuperar solo el entorno Python
├── biomed-control.sh        # ← Script helper interactivo (servicios)
├── start_biomed.sh          # ← Launcher modo desarrollo
├── start_biomed_prod.sh     # ← Launcher modo producción
├── stop_biomed.sh           # ← Detener todo (servicios y modo desarrollo)
├── main.py                  # ← Entry point Edge UI (PyQt6)
├── requirements.txt         # ← Dependencias Python (directas)
├── requirements.lock        # ← Versiones exactas verificadas (constraints)
├── INSTRUCTIVO.md           # ← Este archivo
├── STRUCTURE.md             # ← Arquitectura técnica detallada
│
├── assets/                  # ← Fotos de pacientes y recursos locales
├── config/
│   ├── settings.yaml        # ← Configuración sensores/MQTT/storage
│   └── patient.json         # ← Datos del paciente activo
│
├── data/
│   ├── biomed.db            # ← DB local Edge (datos de demo, en el repo)
│   └── storage.db           # ← DB permanente API (datos de demo, en el repo)
│
└── services/
    ├── mqtt_subscriber.py   # ← Replica MQTT → storage.db
    ├── storage/
    │   └── main.py          # ← FastAPI REST API
    └── webapp/              # ← Next.js PWA
        └── start-https.mjs  # ← Servidor HTTPS producción
```

---

## ✅ Checklist Pre-Uso

- [ ] `sudo systemctl status mosquitto` → activo
- [ ] `./biomed-control.sh status` → todos los servicios activos y "PWA + API responden"
- [ ] `https://harlink.local:3000` → PWA carga con datos en el navegador
- [ ] Sensores físicos conectados (I2C)

---

**Última actualización:** Octubre 2026
**Versión:** 6.0 (servicios de usuario + arranque automático + PWA compilada + proxy /backend)
