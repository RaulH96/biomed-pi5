import sqlite3, json, time
from pathlib import Path

DB_PATH = Path("data/biomed.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  TEXT    NOT NULL,
    started_at  REAL    NOT NULL,
    ended_at    REAL,
    device_id   TEXT    NOT NULL DEFAULT 'pi5-001',
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bp_measurements (
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
CREATE TABLE IF NOT EXISTS bp_raw (
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
CREATE TABLE IF NOT EXISTS spo2_measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    ts          REAL    NOT NULL,
    spo2_pct    REAL    NOT NULL,
    hr_bpm      INTEGER NOT NULL,
    synced      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS spo2_raw (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    spo2_measurement_id INTEGER NOT NULL REFERENCES spo2_measurements(id),
    ir_json             TEXT    NOT NULL,
    red_json            TEXT    NOT NULL,
    thresh_high_json    TEXT    NOT NULL,
    thresh_low_json     TEXT    NOT NULL,
    sample_rate_hz      REAL    NOT NULL DEFAULT 100.0,
    synced              INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS temp_measurements (
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
CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_sessions_synced  ON sessions(synced);
CREATE INDEX IF NOT EXISTS idx_bp_synced        ON bp_measurements(synced);
CREATE INDEX IF NOT EXISTS idx_spo2_synced      ON spo2_measurements(synced);
CREATE INDEX IF NOT EXISTS idx_temp_synced      ON temp_measurements(synced);
"""

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

def open_session(patient_id: str, device_id: str = "pi5-001") -> int:
    conn = get_conn()
    cur  = conn.execute(
        "INSERT INTO sessions (patient_id, started_at, device_id) VALUES (?,?,?)",
        (patient_id, time.time(), device_id)
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid

def close_session(session_id: int):
    conn = get_conn()
    conn.execute("UPDATE sessions SET ended_at=? WHERE id=?",
                 (time.time(), session_id))
    conn.commit()
    conn.close()

def save_bp(session_id: int, result: dict) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO bp_measurements
               (session_id, ts, sys_mmhg, dia_mmhg, map_mmhg, hr_bpm, category)
               VALUES (?,?,?,?,?,?,?)""",
            (session_id, time.time(),
             result["sys"], result["dia"], result["map"],
             result["hr"], result.get("category", ""))
        )
        bp_id = cur.lastrowid
        conn.execute(
            """INSERT INTO bp_raw
               (bp_measurement_id, fs_hz,
                pressure_json, time_json, osc_json, peaks_json, env_json)
               VALUES (?,?,?,?,?,?,?)""",
            (bp_id, result.get("fs", 0.0),
             json.dumps(result["p_arr"].tolist()),
             json.dumps(result["t_arr"].tolist()),
             json.dumps(result["osc"].tolist()),
             json.dumps(result["picos"].tolist()),
             json.dumps(result["env"].tolist()))
        )
        conn.commit()
        return bp_id
    finally:
        conn.close()

def save_spo2(session_id: int, spo2: float, hr: int,
              ir_buf: list, red_buf: list,
              thresh_high: list, thresh_low: list,
              sample_rate: float = 100.0) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO spo2_measurements (session_id, ts, spo2_pct, hr_bpm) VALUES (?,?,?,?)",
            (session_id, time.time(), spo2, hr)
        )
        spo2_id = cur.lastrowid
        conn.execute(
            """INSERT INTO spo2_raw
               (spo2_measurement_id, ir_json, red_json,
                thresh_high_json, thresh_low_json, sample_rate_hz)
               VALUES (?,?,?,?,?,?)""",
            (spo2_id,
             json.dumps(list(ir_buf)),   json.dumps(list(red_buf)),
             json.dumps(list(thresh_high)), json.dumps(list(thresh_low)),
             sample_rate)
        )
        conn.commit()
        return spo2_id
    finally:
        conn.close()

def save_temp(session_id: int, temp_c: float, state: str,
              max_c: float = None, min_c: float = None,
              ambient_c: float = None) -> int:
    conn = get_conn()
    cur  = conn.execute(
        """INSERT INTO temp_measurements
           (session_id, ts, temp_c, state, max_c, min_c, ambient_c)
           VALUES (?,?,?,?,?,?,?)""",
        (session_id, time.time(), temp_c, state, max_c, min_c, ambient_c)
    )
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid

def get_unsynced(table: str, limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE synced=0 ORDER BY id LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_synced(table: str, ids: list[int]):
    if not ids:
        return
    conn = get_conn()
    conn.execute(
        f"UPDATE {table} SET synced=1 WHERE id IN ({','.join('?'*len(ids))})", ids
    )
    conn.commit()
    conn.close()
