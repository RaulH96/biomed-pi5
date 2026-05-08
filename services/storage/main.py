# services/storage/main.py
# FastAPI — API REST del sistema biomed-pi5
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, json
from pathlib import Path
from datetime import datetime

app = FastAPI(
    title="Biomed Pi5 API",
    description="API REST para el sistema de monitoreo biométrico",
    version="1.0.0"
)

# CORS — permite que la PWA (Next.js) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en produccion limitar a la IP de la PWA
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH      = Path("../../data/storage.db")
PATIENT_FILE = Path("../../config/patient.json")


def get_conn():
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row) -> dict:
    return dict(row) if row else None


def rows_to_list(rows) -> list:
    return [dict(r) for r in rows]


# ── Health ────────────────────────────────────────────────────
@app.get("/health")
def health():
    db_ok = DB_PATH.exists()
    return {
        "status":    "ok" if db_ok else "degraded",
        "db":        db_ok,
        "timestamp": datetime.now().isoformat(),
    }


# ── Paciente ──────────────────────────────────────────────────
@app.get("/patient")
def get_patient():
    """Datos del paciente activo desde patient.json"""
    if not PATIENT_FILE.exists():
        raise HTTPException(status_code=404, detail="Sin paciente registrado")
    return json.loads(PATIENT_FILE.read_text())


@app.put("/patient")
def update_patient(data: dict):
    """Actualiza datos del paciente"""
    PATIENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return {"ok": True}


# ── Sesiones ──────────────────────────────────────────────────
@app.get("/sessions")
def list_sessions(limit: int = 20, offset: int = 0, patient_id: str = None):
    """Lista de sesiones ordenadas por fecha descendente"""
    conn = get_conn()
    q    = "SELECT * FROM sessions"
    args = []
    if patient_id:
        q += " WHERE patient_id=?"
        args.append(patient_id)
    q += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
    args += [limit, offset]
    rows = conn.execute(q, args).fetchall()
    conn.close()
    return rows_to_list(rows)


@app.get("/sessions/{session_id}")
def get_session(session_id: int):
    """Detalle completo de una sesión"""
    conn = get_conn()
    session = row_to_dict(
        conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    session["temp"]     = rows_to_list(conn.execute(
        "SELECT id, ts, temp_c, state, max_c, min_c, ambient_c FROM temp_measurements WHERE session_id=? ORDER BY ts",
        (session_id,)).fetchall())
    session["spo2"]     = rows_to_list(conn.execute(
        "SELECT id, ts, spo2_pct, hr_bpm FROM spo2_measurements WHERE session_id=? ORDER BY ts",
        (session_id,)).fetchall())
    session["bp"]       = rows_to_list(conn.execute(
        "SELECT id, ts, sys_mmhg, dia_mmhg, map_mmhg, hr_bpm, category FROM bp_measurements WHERE session_id=? ORDER BY ts",
        (session_id,)).fetchall())
    conn.close()
    return session


# ── Sección PACIENTE ──────────────────────────────────────────
@app.get("/patient/summary")
def patient_summary():
    """
    Última lectura de cada sensor — para dashboard del paciente.
    Devuelve la medición más reciente de cada tipo.
    """
    conn = get_conn()
    temp = row_to_dict(conn.execute(
        "SELECT temp_c, state, ts FROM temp_measurements ORDER BY ts DESC LIMIT 1"
    ).fetchone())
    spo2 = row_to_dict(conn.execute(
        "SELECT spo2_pct, hr_bpm, ts FROM spo2_measurements ORDER BY ts DESC LIMIT 1"
    ).fetchone())
    bp = row_to_dict(conn.execute(
        "SELECT sys_mmhg, dia_mmhg, map_mmhg, hr_bpm, category, ts FROM bp_measurements ORDER BY ts DESC LIMIT 1"
    ).fetchone())
    conn.close()
    return {"temp": temp, "spo2": spo2, "bp": bp}


@app.get("/patient/sessions")
def patient_sessions(limit: int = 10):
    """Últimas sesiones del paciente activo — vista simplificada"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, started_at, ended_at FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows_to_list(rows)


# ── Sección DOCTOR ────────────────────────────────────────────
@app.get("/doctor/sessions")
def doctor_sessions(limit: int = 50, offset: int = 0):
    """Historial completo de sesiones con resumen de mediciones"""
    conn = get_conn()
    sessions = rows_to_list(conn.execute(
        "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall())

    for s in sessions:
        sid = s["id"]
        s["temp_count"] = conn.execute(
            "SELECT COUNT(*) FROM temp_measurements WHERE session_id=?", (sid,)
        ).fetchone()[0]
        s["spo2_count"] = conn.execute(
            "SELECT COUNT(*) FROM spo2_measurements WHERE session_id=?", (sid,)
        ).fetchone()[0]
        s["bp_count"] = conn.execute(
            "SELECT COUNT(*) FROM bp_measurements WHERE session_id=?", (sid,)
        ).fetchone()[0]
    conn.close()
    return sessions


@app.get("/doctor/sessions/{session_id}/waveform/spo2/{measurement_id}")
def doctor_spo2_waveform(session_id: int, measurement_id: int):
    """Señal raw completa de SpO2 — para ver la onda en la PWA"""
    conn = get_conn()
    row = row_to_dict(conn.execute(
        "SELECT * FROM spo2_raw WHERE spo2_measurement_id=?",
        (measurement_id,)
    ).fetchone())
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    # Deserializar JSON arrays
    return {
        "ir":           json.loads(row["ir_json"]),
        "red":          json.loads(row["red_json"]),
        "thresh_high":  json.loads(row["thresh_high_json"]),
        "thresh_low":   json.loads(row["thresh_low_json"]),
        "sample_rate":  row["sample_rate_hz"],
    }


@app.get("/doctor/sessions/{session_id}/waveform/bp/{measurement_id}")
def doctor_bp_waveform(session_id: int, measurement_id: int):
    """Señal raw completa de presión — para ver la onda y envolvente en la PWA"""
    conn = get_conn()
    row = row_to_dict(conn.execute(
        "SELECT * FROM bp_raw WHERE bp_measurement_id=?",
        (measurement_id,)
    ).fetchone())
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    return {
        "pressure": json.loads(row["pressure_json"]),
        "time":     json.loads(row["time_json"]),
        "osc":      json.loads(row["osc_json"]),
        "peaks":    json.loads(row["peaks_json"]),
        "env":      json.loads(row["env_json"]),
        "fs_hz":    row["fs_hz"],
    }


@app.get("/doctor/trends/bp")
def doctor_bp_trends(limit: int = 20):
    """Tendencia de presión arterial — últimas N mediciones"""
    conn = get_conn()
    rows = rows_to_list(conn.execute(
        """SELECT b.ts, b.sys_mmhg, b.dia_mmhg, b.map_mmhg, b.hr_bpm, b.category,
                  s.patient_id
           FROM bp_measurements b
           JOIN sessions s ON s.id = b.session_id
           ORDER BY b.ts DESC LIMIT ?""",
        (limit,)
    ).fetchall())
    conn.close()
    return rows


@app.get("/doctor/trends/spo2")
def doctor_spo2_trends(limit: int = 20):
    """Tendencia de SpO2 — últimas N mediciones"""
    conn = get_conn()
    rows = rows_to_list(conn.execute(
        """SELECT m.ts, m.spo2_pct, m.hr_bpm, s.patient_id
           FROM spo2_measurements m
           JOIN sessions s ON s.id = m.session_id
           ORDER BY m.ts DESC LIMIT ?""",
        (limit,)
    ).fetchall())
    conn.close()
    return rows


@app.get("/doctor/trends/temp")
def doctor_temp_trends(limit: int = 20):
    """Tendencia de temperatura — últimas N mediciones"""
    conn = get_conn()
    rows = rows_to_list(conn.execute(
        """SELECT m.ts, m.temp_c, m.state, m.ambient_c, s.patient_id
           FROM temp_measurements m
           JOIN sessions s ON s.id = m.session_id
           ORDER BY m.ts DESC LIMIT ?""",
        (limit,)
    ).fetchall())
    conn.close()
    return rows


@app.get("/doctor/alerts")
def doctor_alerts(limit: int = 20):
    """Lecturas fuera de rango clínico"""
    conn = get_conn()
    bp_alerts = rows_to_list(conn.execute(
        """SELECT 'bp' as type, ts, sys_mmhg, dia_mmhg, category
           FROM bp_measurements
           WHERE sys_mmhg >= 140 OR dia_mmhg >= 90
           ORDER BY ts DESC LIMIT ?""", (limit,)
    ).fetchall())
    spo2_alerts = rows_to_list(conn.execute(
        """SELECT 'spo2' as type, ts, spo2_pct, hr_bpm
           FROM spo2_measurements
           WHERE spo2_pct < 95
           ORDER BY ts DESC LIMIT ?""", (limit,)
    ).fetchall())
    temp_alerts = rows_to_list(conn.execute(
        """SELECT 'temp' as type, ts, temp_c, state
           FROM temp_measurements
           WHERE state NOT IN ('normal', 'normal_baja')
           ORDER BY ts DESC LIMIT ?""", (limit,)
    ).fetchall())
    conn.close()
    return {
        "bp":   bp_alerts,
        "spo2": spo2_alerts,
        "temp": temp_alerts,
    }


# ── Sección ADMIN ─────────────────────────────────────────────
@app.get("/admin/status")
def admin_status():
    """Estado del sistema — sensores, MQTT, DB"""
    import yaml
    cfg = {}
    try:
        with open("../../config/settings.yaml") as f:
            cfg = yaml.safe_load(f)
    except Exception:
        pass

    conn = get_conn()
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_temp     = conn.execute("SELECT COUNT(*) FROM temp_measurements").fetchone()[0]
    total_spo2     = conn.execute("SELECT COUNT(*) FROM spo2_measurements").fetchone()[0]
    total_bp       = conn.execute("SELECT COUNT(*) FROM bp_measurements").fetchone()[0]
    unsynced_bp    = conn.execute("SELECT COUNT(*) FROM bp_measurements WHERE synced=0").fetchone()[0]
    unsynced_spo2  = conn.execute("SELECT COUNT(*) FROM spo2_measurements WHERE synced=0").fetchone()[0]
    unsynced_temp  = conn.execute("SELECT COUNT(*) FROM temp_measurements WHERE synced=0").fetchone()[0]
    conn.close()

    return {
        "db": {
            "sessions":      total_sessions,
            "temp_readings": total_temp,
            "spo2_readings": total_spo2,
            "bp_readings":   total_bp,
        },
        "mqtt": {
            "unsynced_bp":   unsynced_bp,
            "unsynced_spo2": unsynced_spo2,
            "unsynced_temp": unsynced_temp,
            "broker":        cfg.get("mqtt", {}).get("broker_host", "?"),
            "port":          cfg.get("mqtt", {}).get("broker_port", 1883),
        },
        "sensors": cfg.get("sensors", {}),
        "storage": cfg.get("storage", {}),
    }


@app.get("/admin/settings")
def admin_settings():
    """Configuración actual del sistema"""
    import yaml
    try:
        with open("../../config/settings.yaml") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
