import os
os.environ["BLINKA_RASPBERRY_PI"] = "1"

import time
import numpy as np
import matplotlib
matplotlib.use('Agg')  # sin display
import matplotlib.pyplot as plt
import board
import busio
import adafruit_mlx90640

# Inicializar I²C y sensor
i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
sensor = adafruit_mlx90640.MLX90640(i2c)
sensor.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

frame = [0] * 768
OUTPUT = "tools/thermal_frame.png"

print("Capturando frames — Ctrl+C para detener")
while True:
    try:
        sensor.getFrame(frame)
        matrix = np.array(frame).reshape((24, 32))

        fig, ax = plt.subplots()
        img = ax.imshow(matrix, vmin=20, vmax=40, cmap="inferno", interpolation="bicubic")
        plt.colorbar(img, label="°C")
        ax.set_title(f"MLX90640  |  Máx: {matrix.max():.1f}°C  Mín: {matrix.min():.1f}°C")
        plt.tight_layout()
        plt.savefig(OUTPUT)
        plt.close()

        print(f"Frame guardado → {OUTPUT}  |  Máx: {matrix.max():.1f}°C  Mín: {matrix.min():.1f}°C")
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("Detenido.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)