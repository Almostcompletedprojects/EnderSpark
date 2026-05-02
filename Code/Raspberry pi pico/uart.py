from machine import Pin, UART, ADC
import time

# UART vers Marlin
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Potentiomètre sur GP26 (ADC0)
pot = ADC(26)

# Trigger (pull-up)
trigger = Pin(16, Pin.IN, Pin.PULL_UP)

last_state = 1
last_speed = -1  # pour éviter spam UART

def set_fan(speed):
    uart.write(f"M106 S{speed}\n".encode())

while True:
    state = trigger.value()

    # Si bouton appuyé → ventilateur contrôlé par pot
    if state == 0:
        raw = pot.read_u16()              # 0–65535
        speed = raw * 255 // 65535       # 0–255

        # envoi seulement si changement significatif
        if abs(speed - last_speed) > 2:
            set_fan(speed)
            print("Fan:", speed)
            last_speed = speed

    # Si bouton relâché → vitesse fixe (ex 150)
    else:
        if last_speed != 150:
            set_fan(150)
            print("Fan fixe: 150")
            last_speed = 150

    last_state = state
    time.sleep_ms(100)
