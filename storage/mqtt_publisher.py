import json, time, threading
import paho.mqtt.client as mqtt
from storage.db import get_unsynced, mark_synced
import yaml

with open("config/settings.yaml") as f:
    _cfg = yaml.safe_load(f).get("mqtt", {})

MQTT_HOST  = _cfg.get("broker_host", "localhost")
MQTT_PORT  = _cfg.get("broker_port", 1883)
DEVICE_ID  = _cfg.get("device_id",   "pi5-001")

TOPIC_BP      = f"biomed/{DEVICE_ID}/bp"
TOPIC_SPO2    = f"biomed/{DEVICE_ID}/spo2"
TOPIC_TEMP    = f"biomed/{DEVICE_ID}/temp"
TOPIC_BP_LIVE   = f"biomed/{DEVICE_ID}/bp/live"
TOPIC_SPO2_LIVE = f"biomed/{DEVICE_ID}/spo2/live"
TOPIC_TEMP_LIVE = f"biomed/{DEVICE_ID}/temp/live"


class MQTTPublisher:
    def __init__(self):
        self._client    = mqtt.Client(client_id=DEVICE_ID, clean_session=True)
        self._connected = False
        self._lock      = threading.Lock()
        self._active    = True
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        threading.Thread(target=self._connection_loop, daemon=True).start()
        threading.Thread(target=self._sync_loop,       daemon=True).start()

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = rc == 0
        print(f"[MQTT] {'Conectado' if rc==0 else f'Error rc={rc}'} "
              f"a {MQTT_HOST}:{MQTT_PORT}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            print(f"[MQTT] Desconectado rc={rc}")

    def _connection_loop(self):
        while self._active:
            if not self._connected:
                try:
                    self._client.connect(MQTT_HOST, MQTT_PORT, 60)
                    self._client.loop_start()
                except Exception as e:
                    print(f"[MQTT] No se pudo conectar: {e}")
            time.sleep(10)

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        if not self._connected:
            return False
        try:
            with self._lock:
                r = self._client.publish(topic, json.dumps(payload), qos=qos)
            return r.rc == 0
        except Exception as e:
            print(f"[MQTT] Error: {e}")
            return False

    def publish_live(self, topic: str, payload: dict):
        """QoS=0 para live — velocidad sobre garantia."""
        if self._connected:
            self._client.publish(topic, json.dumps(payload), qos=0)

    def _sync_loop(self):
        while self._active:
            time.sleep(30)
            if not self._connected:
                continue
            for table, topic in [
                ("bp_measurements",  TOPIC_BP),
                ("spo2_measurements", TOPIC_SPO2),
                ("temp_measurements", TOPIC_TEMP),
            ]:
                rows = get_unsynced(table, 50)
                ids  = [r["id"] for r in rows
                        if self.publish(topic, {**r, "device_id": DEVICE_ID})]
                if ids:
                    mark_synced(table, ids)
                    print(f"[MQTT] Sync {table}: {len(ids)} registros")

    def publish_bp(self, bp_id: int, result: dict, session_id: int):
        self.publish(TOPIC_BP, {
            "device_id": DEVICE_ID, "session_id": session_id,
            "bp_id": bp_id,         "ts": time.time(),
            "sys": result["sys"],   "dia": result["dia"],
            "map": result["map"],   "hr":  result["hr"],
            "category": result.get("category", ""),
        })

    def publish_spo2(self, spo2_id: int, spo2: float, hr: int, session_id: int):
        self.publish(TOPIC_SPO2, {
            "device_id": DEVICE_ID, "session_id": session_id,
            "spo2_id": spo2_id,     "ts": time.time(),
            "spo2": spo2,           "hr": hr,
        })

    def publish_temp(self, temp_id: int, temp_c: float, state: str, session_id: int):
        self.publish(TOPIC_TEMP, {
            "device_id": DEVICE_ID, "session_id": session_id,
            "temp_id": temp_id,     "ts": time.time(),
            "temp_c": temp_c,       "state": state,
        })

    def shutdown(self):
        self._active = False
        self._client.loop_stop()
        self._client.disconnect()
