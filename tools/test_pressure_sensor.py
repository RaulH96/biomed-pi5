# blood-pressure-test/test_presion.py
# Este script es para probar el sensor de presión sin necesidad de usar la bomba o válvula.
# Se puede usar para verificar que el sensor esté conectado correctamente y que las lecturas sean razonables 
# al aplicar presión manualmente (por ejemplo, apretando el sensor con la mano).

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import lgpio
import time

# ── GPIO ──────────────────────────────────────────
PIN_BOMBA   = 17
PIN_VALVULA = 27

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, PIN_BOMBA,   0)
lgpio.gpio_claim_output(h, PIN_VALVULA, 0)

# ── ADS1115 ───────────────────────────────────────
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 2/3  # PGA ±6.144V — cubre 0–4.7V del MPX5050

canal = AnalogIn(ads, 0)

# ── Conversión ────────────────────────────────────
def voltaje_a_mmhg(v):
    kpa  = (v - 0.2) * (50.0 / (4.7 - 0.2))
    mmhg = kpa * 7.50062
    return max(0, kpa), max(0, mmhg)

# ── Control bombas ────────────────────────────────
def bomba_on():
    lgpio.gpio_write(h, PIN_VALVULA, 1)
    time.sleep(0.05)
    lgpio.gpio_write(h, PIN_BOMBA, 1)

def bomba_off():
    lgpio.gpio_write(h, PIN_BOMBA, 0)

def desinflar():
    lgpio.gpio_write(h, PIN_BOMBA,   0)
    lgpio.gpio_write(h, PIN_VALVULA, 0)

def todo_off():
    lgpio.gpio_write(h, PIN_BOMBA,   0)
    lgpio.gpio_write(h, PIN_VALVULA, 0)

# ── Lectura continua ──────────────────────────────
def leer(mostrar=True):
    v    = canal.voltage
    kpa, mmhg = voltaje_a_mmhg(v)
    if mostrar:
        print(f"  {v:.4f}V  {kpa:6.2f} kPa  {mmhg:6.1f} mmHg", end='\r')
    return v, kpa, mmhg

# ── Menú ──────────────────────────────────────────
print("\nComandos:")
print("  i = inflar        d = desinflar")
print("  b/B = bomba ON/OFF")
print("  v/V = valvula cerrar/abrir")
print("  l = leer presion continuo")
print("  x = todo OFF      q = salir\n")

try:
    while True:
        cmd = input("> ").strip()

        if cmd == 'i':
            bomba_on()
            print("Inflando... (Enter para detener bomba)")
            try:
                while True:
                    leer()
                    time.sleep(0.1)
            except KeyboardInterrupt:
                bomba_off()
                print("\nBomba detenida — presion mantenida")

        elif cmd == 'd':
            desinflar()
            print("Desinflando...")

        elif cmd == 'b':
            lgpio.gpio_write(h, PIN_BOMBA, 1)
            print("Bomba ON")

        elif cmd == 'B':
            lgpio.gpio_write(h, PIN_BOMBA, 0)
            print("Bomba OFF")

        elif cmd == 'v':
            lgpio.gpio_write(h, PIN_VALVULA, 1)
            print("Valvula cerrada")

        elif cmd == 'V':
            lgpio.gpio_write(h, PIN_VALVULA, 0)
            print("Valvula abierta")

        elif cmd == 'l':
            print("Leyendo... Ctrl+C para volver al menu\n")
            print(f"{'Voltaje':>12} {'kPa':>10} {'mmHg':>10}")
            print("-" * 36)
            try:
                while True:
                    leer()
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n")

        elif cmd == 'x':
            todo_off()
            print("Todo OFF")

        elif cmd == 'q':
            break

except KeyboardInterrupt:
    pass
finally:
    todo_off()
    lgpio.gpiochip_close(h)
    print("\nGPIO liberado.")