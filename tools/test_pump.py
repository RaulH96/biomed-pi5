# blood-pressure-test/pump_test.py
# Bomba inflado  → GPIO 17 (pin 11)
# Válvula vacío  → GPIO 27 (pin 13)
#este es un script de prueba para verificar el funcionamiento 
#de la bomba y válvula sin necesidad de leer el sensor. 
#Se puede usar para verificar que los transistores y conexiones 
#estén correctas antes de probar con el sensor de presión.

import lgpio
import time

PIN_BOMBA   = 17
PIN_VALVULA = 27

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, PIN_BOMBA,   0)
lgpio.gpio_claim_output(h, PIN_VALVULA, 0)

def bomba_on():
    lgpio.gpio_write(h, PIN_BOMBA, 1)
    print("Bomba ON")

def bomba_off():
    lgpio.gpio_write(h, PIN_BOMBA, 0)
    print("Bomba OFF")

def valvula_on():
    lgpio.gpio_write(h, PIN_VALVULA, 1)
    print("Valvula cerrada")

def valvula_off():
    lgpio.gpio_write(h, PIN_VALVULA, 0)
    print("Valvula abierta")

def todo_off():
    bomba_off()
    valvula_off()

def ciclo_prueba():
    print("Inflando 3s...")
    valvula_on()
    time.sleep(0.05)
    bomba_on()
    time.sleep(3)

    print("Manteniendo 2s...")
    bomba_off()
    time.sleep(2)

    print("Desinflando...")
    valvula_off()
    time.sleep(3)
    print("Ciclo completo.")

print("Comandos: i=inflar  d=desinflar  p=ciclo  b(on)/B(off)=bomba  v(on)/V(off)=valvula  x=todo off  q=salir")

try:
    while True:
        cmd = input("> ").strip()

        if   cmd == 'i': valvula_on();  time.sleep(0.05); bomba_on()
        elif cmd == 'd': bomba_off();   valvula_off()
        elif cmd == 'p': ciclo_prueba()
        elif cmd == 'b': bomba_on()
        elif cmd == 'B': bomba_off()
        elif cmd == 'v': valvula_on()
        elif cmd == 'V': valvula_off()
        elif cmd == 'x': todo_off()
        elif cmd == 'q': break
        else: print("Comando no reconocido")

except KeyboardInterrupt:
    pass
finally:
    todo_off()
    lgpio.gpiochip_close(h)
    print("GPIO liberado.")