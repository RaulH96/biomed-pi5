import os
os.environ["BLINKA_RASPBERRY_PI"] = "1"

import numpy as np
import board
import busio
import adafruit_mlx90640

class MLX90640Driver:
    def __init__(self, refresh_rate=adafruit_mlx90640.RefreshRate.REFRESH_4_HZ):
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        self.sensor = adafruit_mlx90640.MLX90640(i2c)
        self.sensor.refresh_rate = refresh_rate
        self._buffer = [0] * 768

    def read_frame(self) -> np.ndarray:
        """Retorna matriz (24, 32) con temperaturas en °C"""
        self.sensor.getFrame(self._buffer)
        return np.array(self._buffer).reshape((24, 32))