# 🩺 BioMed Pi5 — Instructivo de servicios

## Requisitos previos
- Raspberry Pi 5 encendida y conectada a la red
- IP de la Pi: `192.168.1.75` (fija, ver sección de red)
- Desde tu cel/PC accedes por esa IP en la misma red WiFi

---

## 🚀 Modo DESARROLLO (uso diario)

Abre **3 terminales** en la Pi (o usa tmux).

### Terminal 1 — Interfaz física (PyQt6)
```bash
cd /home/harlink/biomed-pi5
source .venv/bin/activate
python main.py
```

### Terminal 2 — API REST (FastAPI)
```bash
cd /home/harlink/biomed-pi5/services/storage
source /home/harlink/biomed-pi5/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 3 — Webapp (Next.js dev)
```bash
cd /home/harlink/biomed-pi5/services/webapp
./node_modules/.bin/next dev --port 3000
```

### Acceso desde tu red local
| Servicio | URL |
|----------|-----|
| Webapp   | http://192.168.1.75:3000 |
| API docs | http://192.168.1.75:8000/docs |

> ⚠️ En modo dev la PWA **no se puede instalar** en el celular.
> El hot reload funciona: guardas el archivo y el navegador se actualiza solo.

---

## 📱 Modo PRODUCCIÓN (para instalar como app en el celular)

### Paso 1 — Matar servicios anteriores
```bash
fuser -k 3000/tcp
```

### Paso 2 — Build y arranque con HTTPS
```bash
cd /home/harlink/biomed-pi5/services/webapp
npm run build && node start-https.mjs
```
> El build tarda ~2 minutos en la Pi. Solo necesitas hacerlo cuando cambies código.

### Paso 3 — Instalar en el celular

**Android (Chrome):**
1. Abre `https://192.168.1.75:3000` en Chrome (con la **s** en https)
2. Chrome muestra advertencia de seguridad → toca **"Avanzado"** → **"Continuar de todas formas"**
3. Menú (⋮) → **"Agregar a pantalla de inicio"**
4. Confirma → ya aparece como app

**iPhone (Safari):**
1. Abre `https://192.168.1.75:3000` en Safari
2. Safari muestra advertencia → toca **"Mostrar detalles"** → **"Visitar este sitio web"**
3. Botón compartir (⬆) → **"Agregar a pantalla de inicio"**
4. Confirma → ya aparece como app

> ⚠️ La PWA instalada solo funciona cuando estás en la misma red WiFi que la Pi.
> Si la Pi está apagada, la app no carga.

---

## 🌐 Red — IP fija en la Pi

La Pi tiene configurada IP estática para que siempre sea `192.168.1.75`
sin importar cuántas veces se reinicie.

### Configuración aplicada (ya hecha)
```bash
sudo nmcli connection modify "netplan-wlan0-INFINITUM17BB" \
  ipv4.addresses 192.168.1.75/24 \
  ipv4.gateway 192.168.1.1 \
  ipv4.dns "8.8.8.8 8.8.4.4" \
  ipv4.method manual

sudo nmcli connection up "netplan-wlan0-INFINITUM17BB"
```

### Verificar que la IP está activa
```bash
ip addr show wlan0
# Debe mostrar: inet 192.168.1.75/24 ... valid_lft forever
```

### ⚠️ Si llevas la Pi a otra red WiFi

Si cambias de red (otra casa, trabajo, etc.) la IP fija puede causar que
la Pi no se conecte si esa red usa un rango diferente (ej. `192.168.0.x`).

**Volver a IP dinámica temporalmente:**
```bash
sudo nmcli connection modify "netplan-wlan0-INFINITUM17BB" \
  ipv4.method auto \
  ipv4.addresses "" \
  ipv4.gateway "" \
  ipv4.dns ""

sudo nmcli connection up "netplan-wlan0-INFINITUM17BB"

# Ver qué IP te asignó la nueva red
ip addr show wlan0
```

**Volver a IP fija cuando regreses a casa:**
```bash
sudo nmcli connection modify "netplan-wlan0-INFINITUM17BB" \
  ipv4.addresses 192.168.1.75/24 \
  ipv4.gateway 192.168.1.1 \
  ipv4.dns "8.8.8.8 8.8.4.4" \
  ipv4.method manual

sudo nmcli connection up "netplan-wlan0-INFINITUM17BB"
```

> 💡 En una red nueva también tendrías que regenerar el certificado HTTPS
> (ver sección de certificado) y reinstalar la PWA en el cel.

---

## 🔒 Certificado HTTPS (mkcert)

El certificado permite instalar la PWA en Chrome. Válido hasta **agosto 2028**.

### Archivos del certificado
```
services/webapp/192.168.1.75.pem       ← certificado público
services/webapp/192.168.1.75-key.pem   ← clave privada
```

### Si cambias de red y necesitas regenerar el certificado
```bash
cd /home/harlink/biomed-pi5/services/webapp

# Ver la nueva IP primero
ip addr show wlan0

# Generar nuevo certificado para la nueva IP (ej. 192.168.0.50)
mkcert 192.168.0.50

# Actualizar start-https.mjs con el nuevo nombre de archivo
nano start-https.mjs
# Cambia las líneas:
#   key:  readFileSync("./192.168.0.50-key.pem")
#   cert: readFileSync("./192.168.0.50.pem")
```

---

## 🔧 Comandos útiles

### Ver qué está corriendo en un puerto
```bash
fuser 3000/tcp
fuser 8000/tcp
```

### Matar un puerto
```bash
fuser -k 3000/tcp
fuser -k 8000/tcp
```

### Verificar que la API responde
```bash
curl http://localhost:8000/health
# Debe responder: {"status":"ok","db":true,...}
```

### Ver IP actual de la Pi
```bash
ip addr show wlan0
```

---

## 🔁 Flujo de trabajo recomendado

```
Desarrollo diario
      ↓
  next dev (http)     ← hot reload, rápido, sin PWA
      ↓
¿Quieres probar en el cel instalada?
      ↓
  npm run build       ← tarda ~2 min, solo cuando cambies código
  node start-https.mjs← HTTPS, PWA instalable
      ↓
Abre https://192.168.1.75:3000 en Chrome
Acepta advertencia de seguridad
Menú → Agregar a pantalla de inicio
```

---

## 🐛 Problemas frecuentes

| Problema | Solución |
|----------|----------|
| `EADDRINUSE: port 3000` | `fuser -k 3000/tcp` y vuelve a arrancar |
| La webapp no carga desde el cel | Verifica que el cel y la Pi estén en el mismo WiFi |
| La API no responde | `curl http://localhost:8000/health` |
| Cambios en código no se ven | En dev se actualizan solos. En prod hay que hacer `npm run build` de nuevo |
| PWA instalada no abre | Verifica que `node start-https.mjs` esté corriendo (no `next dev`) |
| Chrome dice "sitio no seguro" | Normal — es certificado local. Toca "Avanzado" → "Continuar de todas formas" |
| Pi no se conecta al WiFi en otra red | Volver a IP dinámica (ver sección de red) |
| Error TypeScript en build | Revisa el error, corrige el archivo indicado y vuelve a hacer build |
| Certificado expirado o IP cambió | Regenerar con `mkcert <nueva-ip>` y actualizar `start-https.mjs` |

---

## 📁 Estructura del proyecto
```
biomed-pi5/
├── main.py                      ← Interfaz PyQt6 (sensores físicos)
├── .venv/                       ← Entorno virtual Python
├── data/biomed.db               ← Base de datos SQLite
├── config/
│   ├── settings.yaml            ← Calibración sensores
│   └── patient.json             ← Datos paciente activo
└── services/
    ├── storage/
    │   └── main.py              ← API FastAPI (puerto 8000)
    └── webapp/
        ├── .env.local           ← NEXT_PUBLIC_API_URL=http://192.168.1.75:8000
        ├── next.config.ts       ← Config Next.js + PWA
        ├── start-https.mjs      ← Servidor HTTPS para producción
        ├── 192.168.1.75.pem     ← Certificado HTTPS (válido hasta 2028)
        ├── 192.168.1.75-key.pem ← Clave privada del certificado
        └── public/
            └── manifest.json    ← Config instalación PWA
```
