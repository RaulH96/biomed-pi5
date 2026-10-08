#!/usr/bin/env python3
"""
generar_demo.py — Datos de demo realistas para biomed-pi5

Regenera data/biomed.db (Edge) y data/storage.db (la que consume la PWA) con
el mismo contenido: sesiones de los últimos N días para el paciente de
config/patient.json, con mediciones clínicamente coherentes y señales crudas
sintéticas con forma fisiológica:

  · SpO2: fotopletismografía (PPG) IR y roja con onda de pulso y muesca
    dícrota, arritmia sinusal respiratoria, modulación respiratoria y ruido.
    La relación entre los canales corresponde al SpO2 guardado
    (SpO2 ≈ 110 − 25·R).
  · Presión: desinflado del brazalete con oscilaciones por latido cuya
    envolvente es máxima en la presión media (MAP). La sistólica, la
    diastólica y la MAP guardadas se obtienen DE la señal con el método de
    razones (0.55 · máx y 0.75 · máx), así que las gráficas y los números
    siempre coinciden.

Historia clínica de la demo (paciente con hipertensión tratada con
nifedipino): la presión baja de forma gradual a lo largo del periodo, las
mañanas salen algo más altas, y hay un episodio de febrícula de 3 días.

USO (con los servicios detenidos, porque se reemplazan las bases):
    ./biomed-control.sh stop
    .venv/bin/python tools/generar_demo.py            # 30 días hasta hoy
    .venv/bin/python tools/generar_demo.py --dias 45 --semilla 3
    ./biomed-control.sh start

Las fechas son relativas al momento en que se ejecuta: volver a correrlo
"actualiza" la demo para que las gráficas de 7 días sigan llenas.
"""
import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEVICE_ID = "pi5-001"

SCHEMA = """
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  TEXT    NOT NULL,
    started_at  REAL    NOT NULL,
    ended_at    REAL,
    device_id   TEXT    NOT NULL DEFAULT 'pi5-001',
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE bp_measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    ts          REAL    NOT NULL,
    sys_mmhg    REAL    NOT NULL,
    dia_mmhg    REAL    NOT NULL,
    map_mmhg    REAL    NOT NULL,
    hr_bpm      INTEGER NOT NULL,
    category    TEXT,
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE bp_raw (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    bp_measurement_id INTEGER NOT NULL REFERENCES bp_measurements(id),
    fs_hz             REAL    NOT NULL,
    pressure_json     TEXT    NOT NULL,
    time_json         TEXT    NOT NULL,
    osc_json          TEXT    NOT NULL,
    peaks_json        TEXT    NOT NULL,
    env_json          TEXT    NOT NULL,
    synced            INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE spo2_measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    ts          REAL    NOT NULL,
    spo2_pct    REAL    NOT NULL,
    hr_bpm      INTEGER NOT NULL,
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE spo2_raw (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    spo2_measurement_id INTEGER NOT NULL REFERENCES spo2_measurements(id),
    ir_json             TEXT    NOT NULL,
    red_json            TEXT    NOT NULL,
    thresh_high_json    TEXT    NOT NULL,
    thresh_low_json     TEXT    NOT NULL,
    sample_rate_hz      REAL    NOT NULL DEFAULT 100.0,
    synced              INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE temp_measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    ts          REAL    NOT NULL,
    temp_c      REAL    NOT NULL,
    state       TEXT,
    max_c       REAL,
    min_c       REAL,
    ambient_c   REAL,
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sessions_patient ON sessions(patient_id);
CREATE INDEX idx_sessions_synced  ON sessions(synced);
CREATE INDEX idx_bp_synced        ON bp_measurements(synced);
CREATE INDEX idx_spo2_synced      ON spo2_measurements(synced);
CREATE INDEX idx_temp_synced      ON temp_measurements(synced);
"""


# ── Clasificaciones (idénticas a processing/temperature.py y pressure.py) ──
def classify_temperature(temp: float) -> str:
    if temp < 35.0:
        return "hipotermia"
    elif temp < 36.1:
        return "normal_baja"
    elif temp <= 37.2:
        return "normal"
    elif temp <= 38.0:
        return "febricula"
    elif temp <= 39.0:
        return "fiebre_moderada"
    elif temp <= 40.0:
        return "fiebre_alta"
    return "fiebre_muy_alta"


def classify_bp(sys_: float, dia: float) -> str:
    if sys_ >= 140 or dia >= 90:
        return "Hipertension"
    elif sys_ >= 130 or dia >= 80:
        return "Elevada"
    return "Normal"


# ── Latidos ────────────────────────────────────────────────────
def beat_times(rng, duration_s: float, hr_bpm: float, resp_hz: float) -> np.ndarray:
    """Inicio de cada latido con variabilidad y arritmia sinusal respiratoria."""
    rr_mean = 60.0 / hr_bpm
    t, out = -rng.uniform(0, rr_mean), []
    while t < duration_s + rr_mean:
        out.append(t)
        rsa = 0.045 * rr_mean * math.sin(2 * math.pi * resp_hz * t)
        t += rr_mean * (1 + 0.025 * rng.standard_normal()) + rsa
    return np.array(out)


def pulse_shape(phase: np.ndarray) -> np.ndarray:
    """Onda de pulso arterial: subida sistólica rápida, descenso diastólico
    exponencial a lo largo de todo el latido, muesca y onda dícrota."""
    peak, floor = 0.15, 0.07                       # floor ≈ valor al final del latido anterior
    up = floor + (1 - floor) * 0.5 * (1 - np.cos(np.pi * np.clip(phase / peak, 0, 1)))
    down = np.exp(-(phase - peak) / 0.32)
    main = np.where(phase < peak, up, down)
    notch = -0.06 * np.exp(-((phase - 0.36) / 0.025) ** 2)
    dicrotic = 0.12 * np.exp(-((phase - 0.43) / 0.05) ** 2)
    return main + notch + dicrotic


def pulse_train(rng, t: np.ndarray, beats: np.ndarray) -> np.ndarray:
    w = np.zeros_like(t)
    for i in range(len(beats) - 1):
        a, b = beats[i], beats[i + 1]
        m = (t >= a) & (t < b)
        w[m] += (1 + 0.04 * rng.standard_normal()) * pulse_shape((t[m] - a) / (b - a))
    return w


# ── SpO2: PPG IR / roja ────────────────────────────────────────
def synth_ppg(rng, spo2: float, hr: float, fs: float = 50.0, seconds: float = 8.0) -> dict:
    n = int(fs * seconds)
    t = np.arange(n) / fs
    resp = rng.uniform(0.2, 0.3)
    w = pulse_train(rng, t, beat_times(rng, seconds, hr, resp))
    w = (w - w.min()) / (w.max() - w.min())

    dc_ir = rng.uniform(160_000, 190_000)
    dc_red = dc_ir * rng.uniform(0.80, 0.88)
    pi_ir = rng.uniform(0.008, 0.016)              # índice de perfusión IR (AC/DC)
    r = (110.0 - spo2) / 25.0                      # razón de razones
    ac_ir, ac_red = pi_ir * dc_ir, r * pi_ir * dc_red

    baseline = 0.18 * np.sin(2 * math.pi * resp * t + rng.uniform(0, 6.3))  # respiración
    drift = rng.uniform(-0.15, 0.15) * t / seconds                           # deriva lenta
    # El sensor mide luz que atraviesa el dedo: en la sístole se absorbe más,
    # así que el pulso aparece como valles en la señal cruda (igual que el MAX30102).
    ir = dc_ir - ac_ir * (w + baseline + drift) + rng.normal(0, 0.025 * ac_ir, n)
    red = dc_red - ac_red * (w + baseline + drift) + rng.normal(0, 0.03 * ac_red, n)

    mean, pp = float(ir.mean()), float(ir.max() - ir.min())
    return {
        "fs": fs,
        "ir": np.round(ir, 1).tolist(),
        "red": np.round(red, 1).tolist(),
        "th_high": [round(mean + 0.2 * pp, 1)] * n,
        "th_low": [round(mean - 0.2 * pp, 1)] * n,
    }


# ── Presión: desinflado oscilométrico ─────────────────────────
def synth_bp(rng, sys_t: float, dia_t: float, hr: float, fs: float = 100.0) -> dict:
    map_t = dia_t + 0.40 * (sys_t - dia_t)
    p0 = min(sys_t + rng.uniform(30, 40), 195.0)
    p_end = max(dia_t - rng.uniform(20, 28), 40.0)
    rate = rng.uniform(2.6, 3.4)                   # mmHg/s, válvula de desinflado
    settle, dump = 1.5, 2.0
    t_defl = (p0 - p_end) / rate
    seconds = settle + t_defl + dump
    n = int(seconds * fs)
    t = np.arange(n) / fs

    cuff = np.empty(n)
    m1 = t < settle
    cuff[m1] = p0 + 3.0 * np.exp(-t[m1] / 0.4)    # pequeño sobreimpulso al cerrar la bomba
    m2 = (t >= settle) & (t < settle + t_defl)
    cuff[m2] = p0 - rate * (t[m2] - settle)
    m3 = t >= settle + t_defl
    cuff[m3] = 30 + (p_end - 30) * np.exp(-(t[m3] - settle - t_defl) / 0.5)

    # Envolvente: gaussiana asimétrica con máximo en MAP, calibrada para que
    # el método de razones devuelva exactamente sys_t / dia_t.
    a_max = rng.uniform(1.6, 2.8)
    w_hi = (sys_t - map_t) / math.sqrt(-math.log(0.55))
    w_lo = (map_t - dia_t) / math.sqrt(-math.log(0.75))

    def envelope(p):
        w_ = np.where(p >= map_t, w_hi, w_lo)
        return a_max * np.exp(-((p - map_t) / w_) ** 2)

    beats = beat_times(rng, seconds, hr, rng.uniform(0.2, 0.3))
    osc = np.zeros(n)
    peaks, env = [], []
    for i in range(len(beats) - 1):
        a, b = beats[i], beats[i + 1]
        m = (t >= a) & (t < b)
        if not m.any():
            continue
        shape = pulse_shape((t[m] - a) / (b - a))
        shape -= shape.mean()                      # componente oscilatoria (pasa-altas)
        amp = float(envelope(np.array([cuff[m].mean()]))[0]) * (1 + 0.04 * rng.standard_normal())
        osc[m] += amp * shape / shape.max()
        if settle < a and b < settle + t_defl:     # solo picos durante el desinflado
            idx = int(np.flatnonzero(m)[np.argmax(osc[m])])
            peaks.append(idx)
            env.append(float(osc[idx]))
    osc += rng.normal(0, 0.02, n)
    pressure = cuff + osc + rng.normal(0, 0.05, n)
    times = t + rng.normal(0, 0.0008, n)          # marcas de tiempo reales con jitter

    # Método de razones sobre la señal sintética, como un tensiómetro: envolvente
    # suavizada (3 latidos) y cruce interpolado entre latidos. Sin suavizar, el
    # ruido latido a latido adelanta el primer cruce y sesga la diastólica.
    env_a, p_pk = np.array(env), cuff[np.array(peaks)]
    env_s = np.convolve(np.pad(env_a, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    k = int(np.argmax(env_s))
    e_max = env_s[k]

    def crossing(i, j, level):                     # presión donde env_s cruza level entre i y j
        e1, e2 = env_s[i], env_s[j]
        f = 0.0 if e2 == e1 else (level - e1) / (e2 - e1)
        return float(p_pk[i] + f * (p_pk[j] - p_pk[i]))

    hi = np.flatnonzero(env_s[:k] < 0.55 * e_max)
    lo = np.flatnonzero(env_s[k:] < 0.75 * e_max)
    sys_m = crossing(hi[-1], hi[-1] + 1, 0.55 * e_max) if len(hi) else float(p_pk[0])
    dia_m = crossing(k + lo[0] - 1, k + lo[0], 0.75 * e_max) if len(lo) else float(p_pk[-1])
    map_m = float(p_pk[k])
    rr = np.diff(beats)
    return {
        "fs": fs,
        "duration": seconds,
        "sys": round(sys_m, 1), "dia": round(dia_m, 1), "map": round(map_m, 1),
        "hr": int(round(60.0 / float(np.median(rr)))),
        "pressure": np.round(pressure, 2).tolist(),
        "time": np.round(times, 3).tolist(),
        "osc": np.round(osc, 3).tolist(),
        "peaks": [int(x) for x in peaks],
        "env": [round(x, 4) for x in env],
    }


# ── Escenario clínico ─────────────────────────────────────────
def build_dataset(rng, days: int, patient_uuid: str, now: datetime) -> list[dict]:
    fever_days = {days - 12: 37.4, days - 11: 37.7, days - 10: 37.3}   # índice de día → temp
    cold_day = days - 21
    sessions = []
    for d in range(days + 1):                      # d = 0 es el día más antiguo
        date = (now - timedelta(days=days - d)).date()
        progress = 1 / (1 + math.exp(-(d - days * 0.35) / (days * 0.12)))  # efecto del tratamiento
        slots = []
        if d == days or rng.random() > 0.12:
            slots.append(("manana", rng.uniform(7.3, 9.0)))
        if rng.random() < 0.35:
            slots.append(("noche", rng.uniform(19.3, 21.0)))
        for slot, hour in slots:
            start = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour)
            if start > now - timedelta(minutes=40):
                continue
            fever = fever_days.get(d)
            morning = slot == "manana"

            sys_t = 146 - 19 * progress + (4 if morning else -3) + rng.normal(0, 3.5)
            dia_t = 93 - 16 * progress + (2 if morning else -2) + rng.normal(0, 2.5)
            dia_t = min(dia_t, sys_t - 32)
            hr = rng.normal(72 if morning else 76, 3.5) + (10 if fever else 0)
            spo2 = float(np.clip(rng.normal(97.3, 0.7) - (1.6 if fever else 0), 94.2, 99.4))
            temp = (fever or float(np.clip(rng.normal(36.6, 0.18), 36.2, 37.1))) + rng.normal(0, 0.05)
            if d == cold_day and morning:
                temp = 35.9
            ambient = rng.uniform(21.5, 23.5) if morning else rng.uniform(23.5, 25.5)

            t0 = start.timestamp()
            temps = [t0 + rng.uniform(25, 40)]
            if rng.random() < 0.5:
                temps.append(temps[0] + rng.uniform(62, 75))
            spo2_ts = [t0 + rng.uniform(70, 95)]
            if rng.random() < 0.3:
                spo2_ts.append(spo2_ts[0] + rng.uniform(92, 110))
            bp_ts = [max(spo2_ts) + rng.uniform(60, 90)]
            if rng.random() < 0.25:
                bp_ts.append(bp_ts[0] + rng.uniform(150, 200))

            s = {"patient_id": patient_uuid, "started_at": t0, "temps": [], "spo2": [], "bp": []}
            for ts in temps:
                tc = round(float(temp + rng.normal(0, 0.06)), 1)
                s["temps"].append({
                    "ts": ts, "temp_c": tc, "state": classify_temperature(tc),
                    "max_c": round(tc + rng.uniform(0.3, 0.6), 1),
                    "min_c": round(ambient - rng.uniform(0.3, 1.2), 1),
                    "ambient_c": round(ambient + rng.normal(0, 0.2), 1),
                })
            for ts in spo2_ts:
                v = round(float(np.clip(spo2 + rng.normal(0, 0.3), 94.0, 99.6)), 1)
                h = int(round(hr + rng.normal(0, 1.5)))
                s["spo2"].append({"ts": ts, "spo2_pct": v, "hr_bpm": h, "raw": synth_ppg(rng, v, h)})
            for i, ts in enumerate(bp_ts):
                drop = 4 * i                       # la segunda toma suele salir algo más baja
                raw = synth_bp(rng, sys_t - drop + rng.normal(0, 1.5), dia_t - drop / 2,
                               hr + rng.normal(0, 1.5))
                s["bp"].append({"ts": ts + raw["duration"], "raw": raw})
            last = max([m["ts"] for k in ("temps", "spo2", "bp") for m in s[k]])
            s["ended_at"] = last + rng.uniform(25, 80)
            sessions.append(s)
    return sessions


# ── Escritura ─────────────────────────────────────────────────
def write_db(path: Path, sessions: list[dict]) -> None:
    tmp = path.with_name(f".{path.name}.nuevo")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    conn.executescript(SCHEMA)
    ids = {"temp": 0, "spo2": 0, "bp": 0}
    for sid, s in enumerate(sessions, start=1):
        conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?,1)",
                     (sid, s["patient_id"], s["started_at"], s["ended_at"], DEVICE_ID))
        for m in s["temps"]:
            ids["temp"] += 1
            conn.execute("INSERT INTO temp_measurements VALUES (?,?,?,?,?,?,?,?,1)",
                         (ids["temp"], sid, m["ts"], m["temp_c"], m["state"],
                          m["max_c"], m["min_c"], m["ambient_c"]))
        for m in s["spo2"]:
            ids["spo2"] += 1
            r = m["raw"]
            conn.execute("INSERT INTO spo2_measurements VALUES (?,?,?,?,?,1)",
                         (ids["spo2"], sid, m["ts"], m["spo2_pct"], m["hr_bpm"]))
            conn.execute("INSERT INTO spo2_raw VALUES (?,?,?,?,?,?,?,1)",
                         (ids["spo2"], ids["spo2"], json.dumps(r["ir"]), json.dumps(r["red"]),
                          json.dumps(r["th_high"]), json.dumps(r["th_low"]), r["fs"]))
        for m in s["bp"]:
            ids["bp"] += 1
            r = m["raw"]
            conn.execute("INSERT INTO bp_measurements VALUES (?,?,?,?,?,?,?,?,1)",
                         (ids["bp"], sid, m["ts"], r["sys"], r["dia"], r["map"], r["hr"],
                          classify_bp(r["sys"], r["dia"])))
            conn.execute("INSERT INTO bp_raw VALUES (?,?,?,?,?,?,?,?,1)",
                         (ids["bp"], ids["bp"], r["fs"], json.dumps(r["pressure"]),
                          json.dumps(r["time"]), json.dumps(r["osc"]),
                          json.dumps(r["peaks"]), json.dumps(r["env"])))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    for suffix in ("-wal", "-shm"):               # un -wal viejo corrompería la base nueva
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    os.replace(tmp, path)


def services_running() -> list[str]:
    found = []
    for cmd in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            c = cmd.read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except OSError:
            continue
        if "mqtt_subscriber.py" in c or "uvicorn main:app" in c or f"{PROJECT_DIR}/main.py" in c:
            found.append(c.strip()[:80])
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=30, help="días hacia atrás desde hoy (30)")
    ap.add_argument("--semilla", type=int, default=7, help="semilla aleatoria, mismo valor = mismos datos (7)")
    ap.add_argument("--salida", type=Path, default=PROJECT_DIR / "data", help="carpeta de las bases (data/)")
    ap.add_argument("--forzar", action="store_true", help="no comprobar si los servicios están corriendo")
    args = ap.parse_args()

    if not args.forzar and (running := services_running()):
        print("Detén primero los servicios (./biomed-control.sh stop); siguen corriendo:")
        for r in running:
            print("  ·", r)
        return 1

    patient = json.loads((PROJECT_DIR / "config" / "patient.json").read_text(encoding="utf-8"))
    if not patient.get("uuid"):
        print("config/patient.json no tiene 'uuid'")
        return 1

    rng = np.random.default_rng(args.semilla)
    sessions = build_dataset(rng, args.dias, patient["uuid"], datetime.now())
    args.salida.mkdir(parents=True, exist_ok=True)
    for name in ("biomed.db", "storage.db"):
        write_db(args.salida / name, sessions)

    n = {k: sum(len(s[k]) for s in sessions) for k in ("temps", "spo2", "bp")}
    first = datetime.fromtimestamp(sessions[0]["started_at"]).strftime("%Y-%m-%d")
    last = datetime.fromtimestamp(sessions[-1]["started_at"]).strftime("%Y-%m-%d %H:%M")
    print(f"✓ {len(sessions)} sesiones ({first} → {last}) para {patient.get('name', '').strip()}")
    print(f"  temperatura: {n['temps']} · SpO2: {n['spo2']} · presión: {n['bp']} (con señales crudas)")
    for name in ("biomed.db", "storage.db"):
        print(f"  {args.salida / name}: {(args.salida / name).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
