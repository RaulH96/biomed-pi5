#!/usr/bin/env python3
"""
Servicio de sincronización de datos RAW
Lee datos raw con synced=0 de biomed.db y los publica vía MQTT
Corre en background cada 30 segundos
"""
import time
import sqlite3
import json
import paho.mqtt.client as mqtt
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
BIOMED_DB = BASE_DIR / 'data' / 'biomed.db'
CONFIG_PATH = BASE_DIR / 'config' / 'settings.yaml'

# Cargar config MQTT
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

BROKER = config['mqtt']['broker_host']
PORT = config['mqtt']['broker_port']
DEVICE_ID = config['mqtt']['device_id']

TOPIC_SPO2 = f"biomed/{DEVICE_ID}/spo2"
TOPIC_BP = f"biomed/{DEVICE_ID}/bp"

class RawSyncService:
    def __init__(self):
        self.client = mqtt.Client(client_id=f"raw-sync-{DEVICE_ID}")
        self.connected = False
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            logger.info(f"✓ Conectado a MQTT {BROKER}:{PORT}")
        except Exception as e:
            logger.error(f"✗ Error conectando a MQTT: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("✓ MQTT conectado")
        else:
            logger.error(f"✗ MQTT error: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning("⚠ MQTT desconectado, reconectando...")
    
    def sync_spo2_raw(self):
        """Sincroniza SpO2 raw con synced=0"""
        conn = sqlite3.connect(BIOMED_DB)
        cursor = conn.execute('''
            SELECT r.id, r.spo2_measurement_id, r.ir_json, r.red_json, 
                   r.thresh_high_json, r.thresh_low_json, r.sample_rate_hz,
                   m.session_id, m.ts, m.spo2_pct, m.hr_bpm
            FROM spo2_raw r
            JOIN spo2_measurements m ON r.spo2_measurement_id = m.id
            WHERE r.synced = 0
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        count = 0
        
        for row in rows:
            raw_id, mid, ir_json, red_json, th_json, tl_json, fs, session_id, ts, spo2, hr = row
            
            payload = {
                "device_id": DEVICE_ID,
                "session_id": session_id,
                "spo2_id": mid,
                "ts": ts,
                "spo2": spo2,
                "hr": hr,
                "raw": {
                    "ir_json": ir_json,
                    "red_json": red_json,
                    "thresh_high_json": th_json,
                    "thresh_low_json": tl_json,
                    "sample_rate_hz": fs or 25.0
                }
            }
            
            try:
                result = self.client.publish(TOPIC_SPO2, json.dumps(payload), qos=1)
                result.wait_for_publish()
                
                if result.is_published():
                    conn.execute('UPDATE spo2_raw SET synced = 1 WHERE id = ?', (raw_id,))
                    conn.commit()
                    count += 1
            except Exception as e:
                logger.error(f"✗ Error publicando SpO2 raw {mid}: {e}")
        
        conn.close()
        return count
    
    def sync_bp_raw(self):
        """Sincroniza BP raw con synced=0"""
        conn = sqlite3.connect(BIOMED_DB)
        cursor = conn.execute('''
            SELECT r.id, r.bp_measurement_id, r.pressure_json, r.time_json,
                   r.osc_json, r.peaks_json, r.env_json, r.fs_hz,
                   m.session_id, m.ts, m.sys_mmhg, m.dia_mmhg, m.map_mmhg, m.hr_bpm, m.category
            FROM bp_raw r
            JOIN bp_measurements m ON r.bp_measurement_id = m.id
            WHERE r.synced = 0
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        count = 0
        
        for row in rows:
            raw_id, mid, p_json, t_json, o_json, pk_json, e_json, fs, session_id, ts, sys, dia, map_val, hr, cat = row
            
            payload = {
                "device_id": DEVICE_ID,
                "session_id": session_id,
                "bp_id": mid,
                "ts": ts,
                "sys": sys,
                "dia": dia,
                "map": map_val,
                "hr": hr,
                "category": cat,
                "raw": {
                    "pressure_json": p_json,
                    "time_json": t_json,
                    "osc_json": o_json,
                    "peaks_json": pk_json,
                    "env_json": e_json,
                    "fs_hz": fs or 100.0
                }
            }
            
            try:
                result = self.client.publish(TOPIC_BP, json.dumps(payload), qos=1)
                result.wait_for_publish()
                
                if result.is_published():
                    conn.execute('UPDATE bp_raw SET synced = 1 WHERE id = ?', (raw_id,))
                    conn.commit()
                    count += 1
            except Exception as e:
                logger.error(f"✗ Error publicando BP raw {mid}: {e}")
        
        conn.close()
        return count
    
    def run(self):
        """Loop principal - sincroniza cada 30 segundos"""
        logger.info("🔄 Servicio de sincronización RAW iniciado")
        logger.info("Sincronizando cada 30 segundos...")
        
        while True:
            try:
                if self.connected:
                    spo2_count = self.sync_spo2_raw()
                    bp_count = self.sync_bp_raw()
                    
                    if spo2_count > 0 or bp_count > 0:
                        logger.info(f"✓ Sincronizados: {spo2_count} SpO2 raw, {bp_count} BP raw")
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("\n👋 Servicio detenido por usuario")
                break
            except Exception as e:
                logger.error(f"✗ Error en loop: {e}")
                time.sleep(30)
        
        self.client.loop_stop()
        self.client.disconnect()

if __name__ == '__main__':
    service = RawSyncService()
    service.run()
