# storage/session_manager.py
import time
import threading
import yaml
from storage.db import (
    init_db, open_session, close_session,
    save_bp, save_spo2, save_temp
)
from storage.mqtt_publisher import MQTTPublisher


def _load_storage_cfg() -> dict:
    try:
        with open("config/settings.yaml") as f:
            return yaml.safe_load(f).get("storage", {})
    except Exception:
        return {}


class SessionManager:
    _instance = None

    @classmethod
    def get(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = SessionManager()
        return cls._instance

    def __init__(self):
        init_db()
        self.mqtt              = MQTTPublisher()
        self._session_id       = None
        self._patient_id       = None  # None = sin sesion activa
        self._lock             = threading.Lock()

        # Leer configuracion desde yaml
        cfg = _load_storage_cfg()
        self._temp_stable_sec   = cfg.get("temp_stable_seconds",       10)
        self._temp_min_interval = cfg.get("temp_min_interval_seconds",  60)
        self._spo2_min_interval = cfg.get("spo2_save_interval_seconds", 90)

        # Estado temperatura
        self._temp_timer_start = None
        self._temp_last_save   = 0.0

        # Estado SpO2
        self._spo2_last_save   = 0.0

        print(f"[SessionManager] Inicializado — "
              f"temp_stable={self._temp_stable_sec}s "
              f"temp_interval={self._temp_min_interval}s "
              f"spo2_interval={self._spo2_min_interval}s")

    # ── Sesion ────────────────────────────────────────────────
    def start_session(self, patient_id: str, patient_uuid: str = None):
        with self._lock:
            if self._session_id:
                close_session(self._session_id)
            self._patient_id       = patient_uuid or patient_id or "anonimo"
            self._session_id       = open_session(self._patient_id)
            self._temp_timer_start = None
            self._temp_last_save   = 0.0
            self._spo2_last_save   = 0.0
            print(f"[Session] Iniciada id={self._session_id} "
                  f"paciente={patient_id or 'anonimo'}")

    def end_session(self):
        with self._lock:
            if self._session_id:
                ended_at = time.time()
                close_session(self._session_id)
                
                # Publicar cierre a MQTT
                try:
                    import json
                    topic = f"biomed/pi5-001/session/end"
                    payload = {
                        "session_id": self._session_id,
                        "ended_at": ended_at
                    }
                    self.mqtt.publish(topic, payload)
                    print(f"[MQTT] Sesión {self._session_id} cerrada publicada")
                except Exception as e:
                    print(f"[MQTT] Error publicando cierre: {e}")
                
                print(f"[Session] Cerrada id={self._session_id}")
                self._session_id = None
                self._patient_id = None
    
    def _ensure_session(self) -> bool:
        """
        Retorna True si hay sesion activa.
        NO crea sesion automatica — el usuario debe iniciarla
        explicitamente desde el dialogo de bienvenida o tab paciente.
        """
        return self._session_id is not None

    def has_session(self) -> bool:
        return self._session_id is not None

    # ── Presion — guardar al terminar medicion ────────────────
    def on_bp_result(self, result: dict) -> bool:
        with self._lock:
            if not self._ensure_session():
                print("[Session] BP — sin sesion activa, ignorando")
                return False
            bp_id = save_bp(self._session_id, result)
            self.mqtt.publish_bp(
                bp_id=bp_id,
                result=result,
                session_id=self._session_id
            )
            print(f"[Session] BP guardado id={bp_id} "
                  f"{result['sys']:.0f}/{result['dia']:.0f} mmHg")
            return True

    # ── SpO2 — guardar con intervalo minimo controlado ────────
    def on_spo2_stable(self, monitor) -> bool:
        """
        Guarda SpO2 solo si:
        - Hay sesion activa
        - Hay lectura valida (spo2 > 0 y bpm > 0)
        - Pasaron al menos spo2_min_interval segundos desde el ultimo guardado
        """
        if not self.has_session():
            return False

        if monitor.spo2 <= 0 or monitor.bpm <= 0:
            return False

        now = time.time()
        if now - self._spo2_last_save < self._spo2_min_interval:
            remaining = self._spo2_min_interval - (now - self._spo2_last_save)
            print(f"[Session] SpO2 — esperando {remaining:.0f}s mas")
            return False

        with self._lock:
            if not self._ensure_session():
                return False
            spo2_id = save_spo2(
                session_id  = self._session_id,
                spo2        = monitor.spo2,
                hr          = monitor.bpm,
                ir_buf      = list(monitor.ir_buffer),
                red_buf     = list(monitor.red_buffer),
                thresh_high = list(monitor.thresh_high_hist),
                thresh_low  = list(monitor.thresh_low_hist),
            )
            self.mqtt.publish_spo2(
                spo2_id=spo2_id,
                spo2=monitor.spo2,
                hr=monitor.bpm,
                session_id=self._session_id,
                ir_buf=list(monitor.ir_buffer),
                red_buf=list(monitor.red_buffer),
                thresh_high=list(monitor.thresh_high_hist),
                thresh_low=list(monitor.thresh_low_hist),
            )
            self._spo2_last_save = now
            print(f"[Session] SpO2 guardado id={spo2_id} "
                  f"spo2={monitor.spo2:.1f}% hr={monitor.bpm}bpm")
            return True

    # ── Temperatura — guardar si estable >= N seg, max 1/min ──
    def on_temp_reading(self, temp_c: float, state: str, **kwargs) -> bool:
        """
        Guarda temperatura solo si:
        - Hay sesion activa
        - Hay persona detectada (temp_c > 0)
        - La persona lleva temp_stable_sec segundos frente al sensor
        - Pasaron al menos temp_min_interval segundos desde el ultimo guardado
        """
        if not self.has_session():
            return False

        now = time.time()

        if temp_c <= 0:
            self._temp_timer_start = None
            return False

        if self._temp_timer_start is None:
            self._temp_timer_start = now
            return False

        elapsed         = now - self._temp_timer_start
        since_last_save = now - self._temp_last_save

        if elapsed >= self._temp_stable_sec and since_last_save >= self._temp_min_interval:
            with self._lock:
                if not self._ensure_session():
                    return False
                temp_id = save_temp(
                    self._session_id, temp_c, state,
                    max_c     = kwargs.get("max_c"),
                    min_c     = kwargs.get("min_c"),
                    ambient_c = kwargs.get("ambient_c"),
                )
                self.mqtt.publish_temp(
                    temp_id, temp_c, state, self._session_id
                )
                self._temp_last_save   = now
                self._temp_timer_start = now
                print(f"[Session] Temp guardada id={temp_id} "
                      f"{temp_c:.1f}°C {state}")
                return True
        return False

    def shutdown(self):
        self.end_session()
        self.mqtt.shutdown()
