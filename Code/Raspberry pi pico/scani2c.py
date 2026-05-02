from machine import Pin, SoftI2C

# Configuration des broches (selon ton montage)
SDA_PIN = 18
SCL_PIN = 19

# On utilise SoftI2C à 100kHz pour être sûr que ça passe avec tes résistances 18k
i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100000)

print("----- Scan I2C en cours -----")

devices = i2c.scan()

if len(devices) == 0:
    print("Aucun périphérique I2C trouvé !")
    print("Conseils :")
    print("1. Vérifie que SDA est sur la Pin 18 et SCL sur la Pin 19.")
    print("2. Vérifie que l'écran est bien alimenté (VCC et GND).")
    print("3. Tes résistances de 18k sont peut-être mal insérées.")
else:
    print(f"{len(devices)} périphérique(s) trouvé(s) :")
    for device in devices:
        print(f"- Adresse décimale : {device}")
        print(f"- Adresse hexadécimale : {hex(device)}")

print("-----------------------------")