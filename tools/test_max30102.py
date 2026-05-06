import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drivers.max30102 import MAX30102Driver
import yaml

with open("config/settings.yaml") as f:
    cfg = yaml.safe_load(f)["sensors"]["max30102"]

d = MAX30102Driver(i2c_bus=cfg["i2c_channel"], address=cfg["i2c_address"])
if not d.begin():
    print("ERROR: Sensor no encontrado.")
    sys.exit(1)

d.setup(power_level=cfg["power_level"], led_mode=cfg["led_mode"],
        sample_rate=cfg["sample_rate"], sample_avg=cfg["sample_average"],
        pulse_width=cfg["pulse_width"])
print("Sensor OK. Coloca el dedo...\n")
try:
    while True:
        d.check()
        while d.available():
            ir  = d.get_ir()
            red = d.get_red()
            d.next_sample()
            estado = "Dedo detectado" if ir > 50000 else "Sin contacto"
            print(f"\r{ir:>12,}  {red:>12,}  {estado}", end="", flush=True)
        time.sleep(0.02)
except KeyboardInterrupt:
    print("\nFinalizado.")
    d.shutdown()
