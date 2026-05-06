# processing/pressure_monitor.py
# Orquesta el ciclo completo de medicion de presion arterial
import time
import threading
import numpy as np
from collections import deque
from drivers.ads1115 import ADS1115Driver
from drivers.pump_valve import PumpValveDriver
from processing.pressure import voltaje_a_mmhg, calcular_bp, classify_bp
import yaml

with open("config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)["sensors"]["pressure"]

META_INFLATE = _cfg["meta_inflate_mmhg"]
META_STOP    = _cfg["meta_stop_mmhg"]
MAX_BUF      = 20000


class PressureMonitor:
    def __init__(self):
        self.adc   = ADS1115Driver(
            channel   = _cfg["adc_channel"],
            gain      = _cfg["adc_gain"],
            data_rate = _cfg["adc_data_rate"],
        )
        self.pump = PumpValveDriver(
            pin_pump  = _cfg["pin_pump"],
            pin_valve = _cfg["pin_valve"],
        )

        # Estado publico
        self.phase        = "idle"   # idle|inflating|deflating|calculating|done|error
        self.current_mmhg = 0.0
        self.result       = None     # dict con sys/dia/map/hr o None
        self.error        = None
        self.connected    = True

        # Buffers
        self._buf_t  = deque(maxlen=MAX_BUF)
        self._buf_p  = deque(maxlen=MAX_BUF)
        self._ses_t  = []
        self._ses_p  = []
        self._grabbing = False
        self._t_ses_ini = 0.0
        self._active    = True

        threading.Thread(target=self._reader_loop, daemon=True).start()
        time.sleep(0.4)

    # ── Hilo lector continuo ─────────────────────────────────
    def _reader_loop(self):
        while self._active:
            try:
                v    = self.adc.read_voltage()
                mmhg = voltaje_a_mmhg(v)
                t    = time.time()
                self.current_mmhg = mmhg
                self._buf_t.append(t)
                self._buf_p.append(mmhg)
                if self._grabbing:
                    self._ses_t.append(t - self._t_ses_ini)
                    self._ses_p.append(mmhg)
            except Exception:
                pass

    # ── Ciclo automatico ─────────────────────────────────────
    def start_measurement(self):
        if self.phase != "idle":
            return
        self.result = None
        self.error  = None
        threading.Thread(target=self._cycle, daemon=True).start()

    def _cycle(self):
        try:
            # Inflar
            self.phase = "inflating"
            self.pump.inflate_start()
            while self.current_mmhg < META_INFLATE:
                time.sleep(0.05)

            # Bajar grabando
            self.pump.pump_off()
            self.phase      = "deflating"
            self._ses_t     = []
            self._ses_p     = []
            self._t_ses_ini = time.time()
            self._grabbing  = True

            while self.current_mmhg > META_STOP:
                time.sleep(0.05)

            self._grabbing = False
            self.pump.valve_open()

            # Calcular
            self.phase = "calculating"
            res, err   = calcular_bp(list(self._ses_p), list(self._ses_t))

            if err:
                self.error = err
                self.phase = "error"
            else:
                cat, col       = classify_bp(res["sys"], res["dia"])
                res["category"] = cat
                res["color"]    = col
                self.result    = res
                self.phase     = "done"

        except Exception as e:
            self.error = str(e)
            self.phase = "error"
            self.pump.all_off()

    # ── Control manual ───────────────────────────────────────
    def deflate(self):
        self._grabbing = False
        self.pump.all_off()
        self.phase = "idle"

    def stop_pump(self):
        self.pump.pump_off()

    def reset(self):
        self.deflate()
        self.result = None
        self.error  = None

    def shutdown(self):
        self._active = False
        self.pump.close()

    # ── Datos para la grafica ────────────────────────────────
    def get_waveform(self):
        """Retorna (t_rel, p) del buffer continuo — ultimos 60s"""
        if not self._buf_t:
            return [], []
        t0    = self._buf_t[0]
        t_rel = [x - t0 for x in self._buf_t]
        return list(t_rel), list(self._buf_p)

    def get_session_waveform(self):
        return list(self._ses_t), list(self._ses_p)
