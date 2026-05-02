from machine import Pin, Timer, SoftI2C, ADC, PWM, UART
import ssd1306
import utime
import neopixel

# ================= CONFIGURATION =================
ADC_VOLT_PIN = 28
ADC_VOLT_2_PIN = 29
LED_PIN = 10
POT_T_ON_PIN = 26
POT_T_OFF_PIN = 27
NEOPIXEL_PIN = 23

SW_SPEED_ENABLE = 16
SW_PWM_ENABLE = 17

UART_TX_PIN = 4
UART_RX_PIN = 5
UART_BAUDRATE = 115200

# Shunt resistor value for current calculation (Ohms)
SHUNT_RESISTOR = 16.3

# Time parameters in microseconds (us)
T_OFF_MIN = 10      
T_OFF_MAX = 100     
T_ON_MIN = 3        
T_ON_MAX = 25       

SPEED_MIN_PERCENT = 50
SPEED_MAX_PERCENT = 200

# Ramp and smoothing parameters
SPEED_ALPHA = 0.2
SPEED_UP_LIMIT = 2.0    
SPEED_DOWN_LIMIT = 10.0 
DEADBAND = 0.8
SPEED_UPDATE_HZ = 20    

# Security & Regulation Parameters
LOW_VOLT_TIME = 1       # Seconds before triggering a hard fault
LOW_VOLT_FACTOR = 0.40  # Percentage of theoretical voltage for dynamic safety
V_MIN_SAFETY = 20.0     # Absolute minimum voltage floor (Merged security)

I_TARGET = 0.8          # Desired average current (Amps)
I_GAIN = 50.0           # Proportional gain for speed control
I_SHORT_CIRCUIT = 4.5   # Current threshold for physical contact detection

# ADC 1 Calibration (Pin 28)
CAL_ADC_VOLT_1 = 1.5
CAL_REAL_VOLT_1 = 43.4
CAL_FACTOR_1 = CAL_REAL_VOLT_1 / CAL_ADC_VOLT_1

# ADC 2 Calibration (Pin 29)
CAL_ADC_VOLT_2 = 1.5
CAL_REAL_VOLT_2 = 43.4 
CAL_FACTOR_2 = CAL_REAL_VOLT_2 / CAL_ADC_VOLT_2

NUM_SAMPLES = 10

# Stability parameters (V1)
V_STABLE_MARGIN = 0.85
V_DROP_THRESHOLD = -2.0
V_DROP_SENSITIVITY = 5.0

# ================= INITIALIZATION =================
i2c = SoftI2C(scl=Pin(19), sda=Pin(18), freq=100000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)
display.rotate(2) 

np = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), 1)

adc1 = ADC(ADC_VOLT_PIN)
adc2 = ADC(ADC_VOLT_2_PIN)

pot_t_on = ADC(POT_T_ON_PIN)
pot_t_off = ADC(POT_T_OFF_PIN)

pwm = PWM(Pin(LED_PIN))
uart = UART(1, baudrate=UART_BAUDRATE, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

sw_speed = Pin(SW_SPEED_ENABLE, Pin.IN, Pin.PULL_UP)
sw_pwm = Pin(SW_PWM_ENABLE, Pin.IN, Pin.PULL_UP)

voltage_samples_1 = []
voltage_samples_2 = []

# ================= FUNCTIONS =================
def set_led(color):
    np[0] = color
    np.write()

def update_display(t_on_us, t_off_us, v_main, current_a, speed_percent):
    display.fill(0)
    display.text(f"ON:{int(t_on_us)}us", 0, 2, 1)
    display.text(f"OFF:{int(t_off_us)}us", 65, 2, 1)
    
    v_int = int(round(v_main))
    display.text(f"V: {v_int}V", 0, 15, 1)
    display.rect(60, 15, 65, 7, 1)
    v_fill = int(min(v_main, 100.0) / 100.0 * 65)
    display.fill_rect(60, 15, v_fill, 7, 1)
    
    display.text(f"I: {current_a:3.1f}A", 0, 30, 1)
    display.rect(60, 30, 65, 7, 1)
    i_fill = int(min(abs(current_a), 6.0) / 10.0 * 65)
    display.fill_rect(60, 30, i_fill, 7, 1)
    
    display.text(f"Speed: {speed_percent}%", 15, 50, 1)
    display.show()

# ================= MAIN PROGRAM =================
def main():
    state = {
        "tension_max": 0.0,
        "pwm_enabled": False,
        "smoothed_speed": 100.0,
        "last_speed_sent": 100.0,
        "old_int_sent": 100,
        "last_freq": -1,
        "fault_active": False,
        "low_volt_cnt": 0,
        "prev_v_avg": 0.0
    }

    def adc_timer_cb(timer):
        # High speed ADC sampling
        val1 = adc1.read_u16()
        v_adc1 = (val1 / 65535) * 3.3
        voltage_samples_1.append(v_adc1 * CAL_FACTOR_1)
        
        val2 = adc2.read_u16()
        v_adc2 = (val2 / 65535) * 3.3
        voltage_samples_2.append(v_adc2 * CAL_FACTOR_2)
        
        if len(voltage_samples_1) > NUM_SAMPLES: voltage_samples_1.pop(0)
        if len(voltage_samples_2) > NUM_SAMPLES: voltage_samples_2.pop(0)

    adc_t = Timer()
    adc_t.init(freq=1000, mode=Timer.PERIODIC, callback=adc_timer_cb)

    def control_loop(timer):
        if not voltage_samples_1 or not voltage_samples_2: return
        v1_avg = sum(voltage_samples_1) / len(voltage_samples_1)
        v2_avg = sum(voltage_samples_2) / len(voltage_samples_2)

        # Current Calculation (Differential voltage over shunt)
        current_amps = abs((v1_avg - v2_avg) / SHUNT_RESISTOR)

        # 1. Read Potentiometers & Compute PWM
        raw_off = pot_t_off.read_u16()
        raw_on = pot_t_on.read_u16()
        t_off_us = T_OFF_MIN + (raw_off * (T_OFF_MAX - T_OFF_MIN) / 65535.0)
        t_on_us = T_ON_MIN + (raw_on * (T_ON_MAX - T_ON_MIN) / 65535.0)
        
        t_off_s, t_on_s = t_off_us / 1_000_000.0, t_on_us / 1_000_000.0
        period = t_on_s + t_off_s
        if period <= 0: period = 0.000001
        
        f_target = int(1.0 / period)
        d_float = t_on_s / period
        d_u16 = int(d_float * 65535)

        pwm_sw = not sw_pwm.value()
        spd_sw = not sw_speed.value()

        # 2. PWM Frequency Update
        if 8 <= f_target <= 500000:
            if abs(f_target - state["last_freq"]) > 1:
                pwm.freq(f_target)
                state["last_freq"] = f_target

        # 3. Fault & LED Management
        if state["fault_active"]:
            set_led((255, 80, 0))
            pwm.duty_u16(65535) # Turn power off
            display.fill(0)
            display.text("!!! FAULT !!!", 15, 24, 1)
            display.text("LOW VOLTAGE V1", 10, 38, 1)
            display.show()
            if not pwm_sw:
                state["fault_active"] = False
                state["low_volt_cnt"] = 0
            return

        # LED color feedback based on active modes
        if pwm_sw and spd_sw: set_led((120, 0, 200))
        elif pwm_sw: set_led((255, 0, 0))
        else: set_led((0, 255, 0))

        # 4. Output Drive & Security Logic
        if pwm_sw:
            if not state["pwm_enabled"]:
                state["tension_max"] = v1_avg
                state["pwm_enabled"] = True
            
            pwm.duty_u16(65535 - d_u16)
            
            # Dynamic Voltage Security
            v_theo = state["tension_max"] * (1.0 - d_float)
            dynamic_thresh = max(V_MIN_SAFETY, v_theo * LOW_VOLT_FACTOR)
            
            if v1_avg < dynamic_thresh:
                state["low_volt_cnt"] += 1
                if state["low_volt_cnt"] > (LOW_VOLT_TIME * SPEED_UPDATE_HZ):
                    state["fault_active"] = True
                    uart.write("M25\n") # Halt G-code execution
            else:
                state["low_volt_cnt"] = 0
        else:
            pwm.duty_u16(65535)
            state["pwm_enabled"] = False

        # 5. Speed Logic (Hybrid Current/Voltage Regulation)
        target_v = 100.0
        if spd_sw and state["pwm_enabled"] and d_float < 0.98:
            
            # A. CRITICAL SECURITY (Absolute Priority)
            # Short circuit detected by current OR voltage floor breach
            if current_amps > I_SHORT_CIRCUIT or v1_avg < V_MIN_SAFETY:
                target_v = SPEED_MIN_PERCENT
                
            else:
                # B. CURRENT REGULATION (Proportional Loop)
                # Positive error = under target -> Speed up
                # Negative error = over target -> Slow down
                current_error = I_TARGET - current_amps
                target_v = 100.0 + (current_error * I_GAIN)
                
                # C. VOLTAGE SENSITIVITY (Delta V)
                # Penalize speed if voltage drops rapidly
                delta_v = v1_avg - state["prev_v_avg"]
                if delta_v < V_DROP_THRESHOLD:
                    target_v -= abs(delta_v) * V_DROP_SENSITIVITY

            # Clamp output within defined limits
            target_v = max(SPEED_MIN_PERCENT, min(SPEED_MAX_PERCENT, target_v))
        else:
            target_v = 100.0
        
        state["prev_v_avg"] = v1_avg

        # 6. Acceleration Ramp & Smoothing
        state["smoothed_speed"] = (SPEED_ALPHA * target_v) + (1.0 - SPEED_ALPHA) * state["smoothed_speed"]
        diff = state["smoothed_speed"] - state["last_speed_sent"]
        
        if abs(diff) > DEADBAND:
            step = (SPEED_UP_LIMIT if diff > 0 else SPEED_DOWN_LIMIT) / SPEED_UPDATE_HZ
            state["last_speed_sent"] += (step if diff > 0 else -step)
        else:
            state["last_speed_sent"] = state["smoothed_speed"]

        # 7. UART Transmission & Display Refresh
        current_spd_int = int(state["last_speed_sent"])
        if current_spd_int != state["old_int_sent"]:
            uart.write(f"M220 S{current_spd_int}\n")
            state["old_int_sent"] = current_spd_int

        update_display(t_on_us, t_off_us, v1_avg, current_amps, current_spd_int)

    # Main control loop timer
    main_t = Timer()
    main_t.init(freq=SPEED_UPDATE_HZ, mode=Timer.PERIODIC, callback=control_loop)

    try:
        while True:
            utime.sleep(1)
    except KeyboardInterrupt:
        adc_t.deinit()
        main_t.deinit()
        pwm.deinit()
        set_led((0,0,0))

if __name__ == "__main__":
    main()