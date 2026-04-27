# drivers/max30102.py
# Driver de bajo nivel para MAX30102 — solo comunicación I2C
import time
from smbus2 import SMBus

# Registros
_INTSTAT1       = 0x00
_INTSTAT2       = 0x01
_INTENABLE1     = 0x02
_INTENABLE2     = 0x03
_FIFOWRITEPTR   = 0x04
_FIFOOVERFLOW   = 0x05
_FIFOREADPTR    = 0x06
_FIFODATA       = 0x07
_FIFOCONFIG     = 0x08
_MODECONFIG     = 0x09
_PARTICLECONFIG = 0x0A
_LED1_PULSEAMP  = 0x0C
_LED2_PULSEAMP  = 0x0D
_LED3_PULSEAMP  = 0x0E
_LED_PROX_AMP   = 0x10
_MULTILEDCFG1   = 0x11
_MULTILEDCFG2   = 0x12
_PARTID         = 0xFF

STORAGE_SIZE = 100

class _SenseRecord:
    def __init__(self):
        self.red   = [0] * STORAGE_SIZE
        self.IR    = [0] * STORAGE_SIZE
        self.green = [0] * STORAGE_SIZE
        self.head  = 0
        self.tail  = 0

class MAX30102Driver:
    def __init__(self, i2c_bus=1, address=0x57):
        self._bus     = SMBus(i2c_bus)
        self._addr    = address
        self.activeLEDs = 0
        self.sense    = _SenseRecord()

    def begin(self) -> bool:
        part = self._read8(_PARTID)
        return part == 0x15

    def setup(self, power_level=0x2F, sample_avg=4, led_mode=2,
              sample_rate=100, pulse_width=411, adc_range=4096):
        self._soft_reset()
        self._write8(_FIFOCONFIG,     0x40 | 0x10)
        self._write8(_MODECONFIG,     0x07 if led_mode == 3 else 0x03)
        self._write8(_PARTICLECONFIG, 0x20 | 0x0C | 0x03)
        self._write8(_LED1_PULSEAMP,  power_level)
        self._write8(_LED2_PULSEAMP,  power_level)
        self._write8(_LED3_PULSEAMP,  power_level)
        self._write8(_LED_PROX_AMP,   power_level)
        self._write8(_MULTILEDCFG1,   0x01 | (0x02 << 4))
        if led_mode == 3:
            self._write8(_MULTILEDCFG2, 0x03)
        self.activeLEDs = led_mode
        self._clear_fifo()

    def check(self) -> int:
        rp = self._read8(_FIFOREADPTR)
        wp = self._read8(_FIFOWRITEPTR)
        n  = (wp - rp) % 32
        if n == 0:
            return 0
        to_read = n * self.activeLEDs * 3
        while to_read > 0:
            chunk = min(to_read, 30 - (30 % (self.activeLEDs * 3)))
            to_read -= chunk
            try:
                data = self._bus.read_i2c_block_data(self._addr, _FIFODATA, chunk)
            except Exception:
                return 0
            i = 0
            while i < len(data):
                self.sense.head = (self.sense.head + 1) % STORAGE_SIZE
                self.sense.red[self.sense.head] = (
                    (data[i] << 16 | data[i+1] << 8 | data[i+2]) & 0x3FFFF
                )
                i += 3
                if self.activeLEDs > 1:
                    self.sense.IR[self.sense.head] = (
                        (data[i] << 16 | data[i+1] << 8 | data[i+2]) & 0x3FFFF
                    )
                    i += 3
                if self.activeLEDs > 2:
                    self.sense.green[self.sense.head] = (
                        (data[i] << 16 | data[i+1] << 8 | data[i+2]) & 0x3FFFF
                    )
                    i += 3
        return n

    def available(self) -> int:
        n = (self.sense.head - self.sense.tail) % STORAGE_SIZE
        return n

    def get_red(self) -> int: return self.sense.red[self.sense.tail]
    def get_ir(self)  -> int: return self.sense.IR[self.sense.tail]

    def next_sample(self):
        if self.available():
            self.sense.tail = (self.sense.tail + 1) % STORAGE_SIZE

    def shutdown(self):
        self._write8(_MODECONFIG, 0x80)

    def _soft_reset(self):
        self._write8(_MODECONFIG, 0x40)
        time.sleep(0.1)

    def _clear_fifo(self):
        self._write8(_FIFOWRITEPTR, 0)
        self._write8(_FIFOOVERFLOW, 0)
        self._write8(_FIFOREADPTR,  0)

    def _read8(self, reg) -> int:
        try:    return self._bus.read_byte_data(self._addr, reg)
        except: return 0

    def _write8(self, reg, val):
        try: self._bus.write_byte_data(self._addr, reg, val)
        except: pass
