# processing/spo2_hr.py
# Algoritmo de detección de SpO2 y BPM para MAX30102
import time
import numpy as np
from collections import deque
from drivers.max30102 import MAX30102Driver
import yaml

with open("config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)["sensors"]["max30102"]

_ALG  = _cfg["algorithm"]
_CAL  = _cfg["calibration"]

class SpO2Monitor:
    def __init__(self):
        self.driver = MAX30102Driver(
            i2c_bus=_cfg["i2c_channel"],
            address=_cfg["i2c_address"]
        )
        self.connected = False

        buf = int(100 * _ALG["adaptive_window"])
        self._filter_ir  = deque(maxlen=6)
        self._filter_red = deque(maxlen=6)
        self.ir_buffer   = deque(maxlen=buf)
        self.red_buffer  = deque(maxlen=buf)
        self.thresh_high_hist = deque(maxlen=buf)
        self.thresh_low_hist  = deque(maxlen=buf)
        self.beat_times  = deque(maxlen=8)

        self.bpm              = 0
        self.spo2             = 0.0
        self.beat_in_progress = False
        self.current_ir       = 0
        self.current_red      = 0
        self.thresh_high      = 0
        self.thresh_low       = 0
        self._last_beat_time  = time.time()

        if self.driver.begin():
            self.driver.setup(
                power_level  = _cfg["power_level"],
                led_mode     = _cfg["led_mode"],
                sample_rate  = _cfg["sample_rate"],
                sample_avg   = _cfg["sample_average"],
                pulse_width  = _cfg["pulse_width"],
            )
            self.connected = True
            print("[SpO2Monitor] Sensor MAX30102 inicializado.")
        else:
            print("[SpO2Monitor] ERROR: Sensor no encontrado.")

    # def update(self) -> dict | None:
    #     """
    #     Llama en loop. Retorna dict con bpm, spo2, beat_in_progress
    #     o None si no hay sensor.
    #     """
    #     if not self.connected:
    #         return None

    #     self.driver.check()
    #     while self.driver.available():
    #         ir_raw  = self.driver.get_ir()
    #         red_raw = self.driver.get_red()
    #         self.driver.next_sample()

    #         if ir_raw < 50000:
    #             self._reset()
    #         else:
    #             self._filter_ir.append(ir_raw)
    #             self.current_ir = sum(self._filter_ir) / len(self._filter_ir)
    #             self.ir_buffer.append(self.current_ir)

    #             self._filter_red.append(red_raw)
    #             self.current_red = sum(self._filter_red) / len(self._filter_red)
    #             self.red_buffer.append(self.current_red)

    #             self._detect_beat()
    #             self.thresh_high_hist.append(self.thresh_high)
    #             self.thresh_low_hist.append(self.thresh_low)

    #     if time.time() - self._last_beat_time > 3.0:
    #         self.bpm  = 0
    #         self.spo2 = 0.0
    #         self.beat_times.clear()

    #     return {
    #         "bpm":              self.bpm,
    #         "spo2":             round(self.spo2, 1),
    #         "beat_in_progress": self.beat_in_progress,
    #         "connected":        self.connected,
    #     }
    
    def update(self) -> dict | None:
        
        if not self.connected:
            return None

        try:
            self.driver.check()
        except Exception as e:
            print(f"[SpO2Monitor] Error en check(): {e}")
            self.connected = False
            return None

        try:
            while self.driver.available():
                ir_raw  = self.driver.get_ir()
                red_raw = self.driver.get_red()
                self.driver.next_sample()

                if ir_raw < 50000:
                    self._reset()
                else:
                    self._filter_ir.append(ir_raw)
                    self.current_ir = sum(self._filter_ir) / len(self._filter_ir)
                    self.ir_buffer.append(self.current_ir)

                    self._filter_red.append(red_raw)
                    self.current_red = sum(self._filter_red) / len(self._filter_red)
                    self.red_buffer.append(self.current_red)

                    self._detect_beat()
                    self.thresh_high_hist.append(self.thresh_high)
                    self.thresh_low_hist.append(self.thresh_low)

        except Exception as e:
            print(f"[SpO2Monitor] Error leyendo muestra: {e}")
            self._reset()
            # No matar connected — puede ser un glitch transitorio I2C

        if time.time() - self._last_beat_time > 3.0:
            self.bpm  = 0
            self.spo2 = 0.0
            self.beat_times.clear()

        return {
            "bpm":              self.bpm,
            "spo2":             round(self.spo2, 1),
            "beat_in_progress": self.beat_in_progress,
            "connected":        self.connected,
        }
    
    def _detect_beat(self) -> bool:
        if len(self.ir_buffer) < 20:
            return False
        local_min = min(self.ir_buffer)
        local_max = max(self.ir_buffer)
        wave      = local_max - local_min
        self.thresh_high = local_min + wave * _ALG["thresh_high"]
        self.thresh_low  = local_min + wave * _ALG["thresh_low"]

        if not self.beat_in_progress:
            if self.current_ir > self.thresh_high and wave > 100:
                self.beat_in_progress = True
                self._last_beat_time  = time.time()
                self.beat_times.append(self._last_beat_time)
                self._calc_bpm()
                self._calc_spo2()
                return True
        else:
            if self.current_ir < self.thresh_low:
                self.beat_in_progress = False
        return False

    def _calc_bpm(self):
        if len(self.beat_times) > 1:
            diffs = np.diff(list(self.beat_times))
            avg   = np.mean(diffs)
            if avg > 0:
                self.bpm = int(60 / avg)

    def _calc_spo2(self):
        if len(self.red_buffer) < 50:
            return
        red = np.array(self.red_buffer)
        ir  = np.array(self.ir_buffer)
        red_dc = np.mean(red);  ir_dc = np.mean(ir)
        red_ac = red.max() - red.min()
        ir_ac  = ir.max()  - ir.min()
        if red_dc > 0 and ir_dc > 0:
            ratio     = (red_ac / red_dc) / (ir_ac / ir_dc)
            spo2_calc = _CAL["spo2_coeff_a"] - (_CAL["spo2_coeff_b"] * ratio)
            self.spo2 = float(min(100, max(80, spo2_calc)))

    def _reset(self):
        self.current_ir = self.current_red = 0
        self.thresh_high = self.thresh_low = 0
        self._filter_ir.clear();  self._filter_red.clear()
        self.ir_buffer.clear();   self.red_buffer.clear()
        self.thresh_high_hist.clear(); self.thresh_low_hist.clear()
        self.beat_times.clear()
        self.beat_in_progress = False
        self.bpm  = 0
        self.spo2 = 0.0

    def shutdown(self):
        self.driver.shutdown()
