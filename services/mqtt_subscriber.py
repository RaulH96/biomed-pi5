#!/usr/bin/env python3
"""
MQTT Subscriber - Replica datos de Edge a Storage DB
Escucha topics: biomed/{device_id}/{temp,spo2,bp}
Soporta datos raw de SpO2 y BP
"""
import paho.mqtt.client as mqtt
import json
import sqlite3
from pathlib import Path
import yaml
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / 'config' / 'settings.yaml'
STORAGE_DB = BASE_DIR / 'data' / 'storage.db'

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

BROKER = config['mqtt']['broker_host']
PORT = config['mqtt']['broker_port']
DEVICE_ID = config['mqtt']['device_id']

TOPICS = [
    f"biomed/{DEVICE_ID}/temp",
    f"biomed/{DEVICE_ID}/spo2",
    f"biomed/{DEVICE_ID}/bp",
    f"biomed/{DEVICE_ID}/session/end", 
]

def init_storage_db():
    """Inicializa storage.db"""
    conn = sqlite3.connect(STORAGE_DB)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        started_at INTEGER NOT NULL,
        ended_at INTEGER,
        device_id TEXT,
        synced INTEGER DEFAULT 1
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS temp_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        ts INTEGER NOT NULL,
        temp_c REAL NOT NULL,
        state TEXT,
        max_c REAL,
        min_c REAL,
        ambient_c REAL,
        synced INTEGER DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS spo2_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        ts INTEGER NOT NULL,
        spo2_pct REAL NOT NULL,
        hr_bpm INTEGER NOT NULL,
        synced INTEGER DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS spo2_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spo2_measurement_id INTEGER NOT NULL,
        ir_json TEXT,
        red_json TEXT,
        thresh_high_json TEXT,
        thresh_low_json TEXT,
        sample_rate_hz REAL,
        FOREIGN KEY (spo2_measurement_id) REFERENCES spo2_measurements(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bp_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        ts INTEGER NOT NULL,
        sys_mmhg REAL NOT NULL,
        dia_mmhg REAL NOT NULL,
        map_mmhg REAL NOT NULL,
        hr_bpm INTEGER,
        category TEXT,
        synced INTEGER DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bp_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bp_measurement_id INTEGER NOT NULL,
        pressure_json TEXT,
        time_json TEXT,
        osc_json TEXT,
        peaks_json TEXT,
        env_json TEXT,
        fs_hz REAL,
        FOREIGN KEY (bp_measurement_id) REFERENCES bp_measurements(id)
    )''')
    
    conn.commit()
    conn.close()
    logger.info(f"✓ Storage DB initialized: {STORAGE_DB}")

def ensure_session_exists(conn, session_id, device_id='pi5-001'):
    """Asegura que la sesión exista en storage.db"""
    c = conn.cursor()
    c.execute('SELECT id FROM sessions WHERE id = ?', (session_id,))
    if not c.fetchone():
        logger.info(f"Creating session {session_id} in storage DB")
        c.execute('''INSERT INTO sessions (id, patient_id, started_at, device_id, synced)
                     VALUES (?, ?, ?, ?, 1)''',
                  (session_id, 'unknown', int(datetime.now().timestamp()), device_id))
        conn.commit()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"✓ Connected to MQTT broker at {BROKER}:{PORT}")
        for topic in TOPICS:
            client.subscribe(topic)
            logger.info(f"✓ Subscribed to {topic}")
    else:
        logger.error(f"✗ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        
        logger.info(f"← Received: {topic.split('/')[-1]} (session {payload.get('session_id')})")
        
        conn = sqlite3.connect(STORAGE_DB)
        c = conn.cursor()
        
        ensure_session_exists(conn, payload['session_id'], payload.get('device_id', 'pi5-001'))
        
        if 'temp' in topic:
            temp_c = payload.get('temp_c') or payload.get('temp')
            if temp_c is None:
                return
                
            c.execute('''INSERT INTO temp_measurements 
                (session_id, ts, temp_c, state, max_c, min_c, ambient_c, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)''',
                (payload['session_id'], int(payload['ts']), temp_c,
                 payload.get('state'), payload.get('max_c'),
                 payload.get('min_c'), payload.get('ambient_c'))
            )
            logger.info(f"  ✓ Temp: {temp_c:.1f}°C ({payload.get('state')})")
            
        elif 'spo2' in topic:
            spo2_pct = payload.get('spo2_pct') or payload.get('spo2')
            hr_bpm = payload.get('hr_bpm') or payload.get('hr')
            
            if spo2_pct is None or hr_bpm is None:
                return
                
            c.execute('''INSERT INTO spo2_measurements 
                (session_id, ts, spo2_pct, hr_bpm, synced)
                VALUES (?, ?, ?, ?, 1)''',
                (payload['session_id'], int(payload['ts']), spo2_pct, hr_bpm)
            )
            mid = c.lastrowid
            
            # Guardar datos raw si existen
            if 'raw' in payload:
                raw = payload['raw']
                c.execute('''INSERT INTO spo2_raw 
                    (spo2_measurement_id, ir_json, red_json, thresh_high_json, thresh_low_json, sample_rate_hz)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (mid, raw.get('ir_json'), raw.get('red_json'),
                     raw.get('thresh_high_json'), raw.get('thresh_low_json'),
                     raw.get('sample_rate_hz', 25.0))
                )
                logger.info(f"  ✓ SpO2: {spo2_pct:.0f}% HR: {hr_bpm} bpm [+raw]")
            else:
                logger.info(f"  ✓ SpO2: {spo2_pct:.0f}% HR: {hr_bpm} bpm")
            
        elif 'bp' in topic:
            sys_mmhg = payload.get('sys_mmhg') or payload.get('sys')
            dia_mmhg = payload.get('dia_mmhg') or payload.get('dia')
            map_mmhg = payload.get('map_mmhg') or payload.get('map')
            hr_bpm = payload.get('hr_bpm') or payload.get('hr')
            
            if sys_mmhg is None or dia_mmhg is None:
                return
                
            c.execute('''INSERT INTO bp_measurements 
                (session_id, ts, sys_mmhg, dia_mmhg, map_mmhg, hr_bpm, category, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)''',
                (payload['session_id'], int(payload['ts']), sys_mmhg,
                 dia_mmhg, map_mmhg, hr_bpm, payload.get('category'))
            )
            mid = c.lastrowid
            
            # Guardar datos raw si existen
            if 'raw' in payload:
                raw = payload['raw']
                c.execute('''INSERT INTO bp_raw 
                    (bp_measurement_id, pressure_json, time_json, osc_json, peaks_json, env_json, fs_hz)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (mid, raw.get('pressure_json'), raw.get('time_json'),
                     raw.get('osc_json'), raw.get('peaks_json'),
                     raw.get('env_json'), raw.get('fs_hz', 100.0))
                )
                logger.info(f"  ✓ BP: {sys_mmhg:.0f}/{dia_mmhg:.0f} mmHg ({payload.get('category')}) [+raw]")
            else:
                logger.info(f"  ✓ BP: {sys_mmhg:.0f}/{dia_mmhg:.0f} mmHg ({payload.get('category')})")
        
        elif 'session/end' in topic:
            # Cerrar sesión en storage.db
            c.execute('UPDATE sessions SET ended_at = ? WHERE id = ?',
                     (int(payload['ended_at']), payload['session_id']))
            logger.info(f"  ✓ Sesión {payload['session_id']} cerrada")
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"✗ Error processing message: {e}")
        import traceback
        traceback.print_exc()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"⚠ Unexpected disconnect (code {rc}), reconnecting...")

def main():
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🔄 Biomed MQTT Subscriber")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    init_storage_db()
    
    client = mqtt.Client(client_id=f"subscriber-{DEVICE_ID}")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    logger.info(f"Connecting to {BROKER}:{PORT}...")
    client.connect(BROKER, PORT, 60)
    
    logger.info("Listening for messages... (Ctrl+C to stop)")
    client.loop_forever()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Subscriber stopped by user")
    except Exception as e:
        logger.error(f"✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
