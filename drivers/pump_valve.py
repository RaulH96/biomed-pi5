# drivers/pump_valve.py
# Control GPIO de bomba y valvula del baumanometro
import lgpio
import time


class PumpValveDriver:
    def __init__(self, pin_pump=17, pin_valve=27):
        self._pin_pump  = pin_pump
        self._pin_valve = pin_valve
        self._h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self._h, pin_pump,  0)
        lgpio.gpio_claim_output(self._h, pin_valve, 0)

    def pump_on(self):
        lgpio.gpio_write(self._h, self._pin_pump, 1)

    def pump_off(self):
        lgpio.gpio_write(self._h, self._pin_pump, 0)

    def valve_close(self):
        lgpio.gpio_write(self._h, self._pin_valve, 1)

    def valve_open(self):
        lgpio.gpio_write(self._h, self._pin_valve, 0)

    def inflate_start(self):
        self.valve_close()
        time.sleep(0.05)
        self.pump_on()

    def deflate(self):
        self.pump_off()
        self.valve_open()

    def all_off(self):
        self.pump_off()
        self.valve_open()

    def close(self):
        self.all_off()
        time.sleep(0.1)
        lgpio.gpiochip_close(self._h)
