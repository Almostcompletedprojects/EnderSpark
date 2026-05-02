from machine import Pin, ADC, PWM
import time

# Broches
LED_PIN = 25
POT_DUTY_PIN = 26  # Potentiomètre pour duty cycle
POT_FREQ_PIN = 27  # Potentiomètre pour fréquence

# Plage de fréquences ajustables
FREQ_MIN = 100     # Hz minimum
FREQ_MAX = 50_000  # Hz maximum

# Initialisation des ADC pour les potentiomètres
pot_duty = ADC(POT_DUTY_PIN)   # Contrôle le duty cycle
pot_freq = ADC(POT_FREQ_PIN)   # Contrôle la fréquence

# Initialisation du PWM
pwm = PWM(Pin(LED_PIN))

print("=== Controle PWM avec deux potentiometres ===")
print(f"Potentiometre pin {POT_DUTY_PIN}: Duty cycle (0% a 100%)")
print(f"Potentiometre pin {POT_FREQ_PIN}: Frequence ({FREQ_MIN} Hz a {FREQ_MAX} Hz)")
print("=============================================")

last_duty = 0
last_freq = 0

try:
    while True:
        # Lecture des potentiomètres
        duty_raw = pot_duty.read_u16()  # 0-65535
        freq_raw = pot_freq.read_u16()  # 0-65535
        
        # Conversion de la fréquence
        # Échelle logarithmique pour meilleur contrôle (optionnel)
        freq_hz = FREQ_MIN + (freq_raw * (FREQ_MAX - FREQ_MIN) // 65535)
        
        # Conversion linéaire simple
        # freq_hz = FREQ_MIN + (freq_raw * (FREQ_MAX - FREQ_MIN) // 65535)
        
        # Application de la fréquence (seulement si changement significatif)
        if abs(freq_hz - last_freq) > 10:  # Seuil de 10 Hz
            pwm.freq(freq_hz)
            last_freq = freq_hz
        
        # Application du duty cycle
        pwm.duty_u16(duty_raw)
        
        # Calcul des pourcentages pour l'affichage
        duty_percent = duty_raw * 100 // 65535
        
        # Affichage seulement si changement significatif
        if abs(duty_percent - last_duty) >= 1 or abs(freq_hz - last_freq) > 10:
            print(f"Freq: {freq_hz:5d} Hz | Duty: {duty_percent:3d}%")
            last_duty = duty_percent
        
        time.sleep(0.05)  # 20 lectures par seconde

except KeyboardInterrupt:
    pwm.deinit()
    print("\nProgramme arrete proprement")

