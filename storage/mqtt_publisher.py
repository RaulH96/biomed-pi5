# storage/mqtt_publisher.py
import time
import threading
import paho.mqtt.client as mqtt
import yaml
import json
import sqlite3
from pathlib import Path

with open("config/settings.yaml") as _f:
    _cfg = yaml.safe_load(_f)["mqtt"]
BROKER    = _cfg["broker_host"]
PORT      = _cfg["broker_port"]
DEVICE_ID = _cfg["device_id"]

TOPIC_TEMP = f"biomed/{DEVICE_ID}/temp"
TOPIC_SPO2 = f"biomed/{DEVICE_ID}/spo2"
TOPIC_BP   = f"biomed/{DEVICE_ID}/bp"

DB_PATH = Path(__file__).parent.parent / "data" / "biomed.db"

class MQTTPublisher:
    def __init__(self):
        self._client = mqtt.Client()
        self._active = False
        try:
            self._client.connect(BROKER, PORT, 60)
            self._client.loop_start()
            self._active = True
            print(f"[MQTT] Conectado a {BROKER}:{PORT}")
        except Exception as e:
            print(f"[MQTT] No disponible: {e}")
    
    def publish(self, topic: str, payload: dict):
        if not self._active:
            return
        self._client.publish(topic, json.dumps(payload), qos=1)
    
    def publish_spo2(self, spo2_id: int, spo2: float, hr: int, session_id: int, 
                     ir_buf=None, red_buf=None, thresh_high=None, thresh_low=None):
        """Publica SpO2 con datos raw opcionales"""
        payload = {
            "device_id": DEVICE_ID,
            "session_id": session_id,
            "spo2_id": spo2_id,
            "ts": time.time(),
            "spo2": spo2,
            "hr": hr,
        }
        
        # Agregar raw si está disponible
        if ir_buf and red_buf:
            payload["raw"] = {
                "ir_json": json.dumps(ir_buf),
                "red_json": json.dumps(red_buf),
                "thresh_high_json": json.dumps(thresh_high) if thresh_high else None,
                "thresh_low_json": json.dumps(thresh_low) if thresh_low else None,
                "sample_rate_hz": 25.0
            }
        
        self.publish(TOPIC_SPO2, payload)
    
    def publish_bp(self, bp_id: int, result: dict, session_id: int):
        """Publica BP con datos raw"""
        payload = {
            "device_id": DEVICE_ID,
            "session_id": session_id,
            "bp_id": bp_id,
            "ts": time.time(),
            "sys": result["sys"],
            "dia": result["dia"],
            "map": result["map"],
            "hr": result["hr"],
            "category": result.get("category", ""),
        }
        
        # Agregar raw si está disponible en result
        if "p_arr" in result and "t_arr" in result:
            payload["raw"] = {
                "pressure_json": json.dumps(result["p_arr"].tolist()),
                "time_json": json.dumps(result["t_arr"].tolist()),
                "osc_json": json.dumps(result["osc"].tolist()),
                "peaks_json": json.dumps(result["picos"].tolist()),
                "env_json": json.dumps(result["env"].tolist()),
                "fs_hz": result.get("fs", 100.0)
            }
        
        topic = f"biomed/{DEVICE_ID}/bp"
        self._client.publish(topic, json.dumps(payload), qos=1)
        
        #self.publish(TOPIC_BP, payload)
    
    def publish_temp(self, temp_id: int, temp_c: float, state: str, session_id: int):
        self.publish(TOPIC_TEMP, {
            "device_id": DEVICE_ID,
            "session_id": session_id,
            "temp_id": temp_id,
            "ts": time.time(),
            "temp_c": temp_c,
            "state": state,
        })
    
    def shutdown(self):
        self._active = False
        self._client.loop_stop()
        self._client.disconnect()
