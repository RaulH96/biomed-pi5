# drivers/ads1115.py
# Comunicacion de bajo nivel con ADS1115 via I2C
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


class ADS1115Driver:
    def __init__(self, channel=0, gain=2/3, data_rate=860):
        i2c        = busio.I2C(board.SCL, board.SDA)
        self._ads  = ADS.ADS1115(i2c)
        self._ads.gain      = gain
        self._ads.data_rate = data_rate
        self._canal = AnalogIn(self._ads, channel)

    def read_voltage(self) -> float:
        return self._canal.voltage
