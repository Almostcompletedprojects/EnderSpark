from machine import ADC, Pin
import utime

# GP28 = ADC2
adc = ADC(28)

VREF = 3.3  # tension Pico

def read_voltage():
    raw = adc.read_u16()
    voltage = raw * VREF / 65535
    return voltage

while True:
    v = read_voltage()
    print("Tension GP28: {:.4f} V".format(v))
    utime.sleep(0.5)