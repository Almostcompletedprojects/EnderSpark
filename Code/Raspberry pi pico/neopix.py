from neopixel import NeoPixel
import machine
import time

# Configuration

# Initialiser les NeoPixels
np = NeoPixel(machine.Pin(23), 1)

# Allumer la LED en rouge
np[0] = (255, 0, 100)  # (Rouge, Vert, Bleu) - valeurs de 0 à 255
np.write()

print("LED NeoPixel allumée en rouge sur le pin 23")

# Garder le programme actif
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Éteindre la LED avant de quitter
    np[0] = (0, 0, 0)
    np.write()
    print("\nLED éteinte")
