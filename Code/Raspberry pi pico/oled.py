from machine import Pin, SoftI2C
import ssd1306
import time

# Configuration I2C - Pins GPIO4 (SDA) et GPIO5 (SCL)
i2c = SoftI2C(scl=Pin(19), sda=Pin(18), freq=400000)

# Initialisation de l'écran (128x64 pixels)
display = ssd1306.SSD1306_I2C(128, 64, i2c)
display.rotate(2)

# Effacer l'écran
display.fill(0)

# Afficher "Bonjour"
display.text("Bonjour !", 30, 20, 1)
display.text("Pico + OLED", 25, 35, 1)

# Mettre à jour l'affichage
display.show()
