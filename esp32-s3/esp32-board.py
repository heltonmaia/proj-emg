"""MicroPython script for ESP32-S3 — streams raw EMG samples via USB-CDC.

Flash this to the ESP32-S3 as ``main.py``. It reads one ADC channel at
SAMPLE_RATE Hz for DURATION_S seconds and prints each sample as a line on
the native USB serial port. A companion host script (``esp32-pc.py``)
parses those lines and writes the CSV.

Wi-Fi and BLE are disabled before sampling to keep the ADC quiet.
"""

import sys
import time
from machine import ADC, Pin

# ---------- Config ----------
SAMPLE_RATE = 1000                       # Hz
DURATION_S = 30
ADC_PIN = 1                              # GPIO1 = ADC1_CH0 (ADC1, NOT ADC2/Wi-Fi)
PERIOD_US = 1_000_000 // SAMPLE_RATE
TOTAL_SAMPLES = SAMPLE_RATE * DURATION_S

# ---------- Silence the radios (keeps ADC clean) ----------
try:
    import network
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)
except Exception:
    pass
try:
    import bluetooth
    bluetooth.BLE().active(False)
except Exception:
    pass

# ---------- ADC ----------
adc = ADC(Pin(ADC_PIN), atten=ADC.ATTN_11DB)   # ~0–3.3 V input range

# ---------- Handshake ----------
# Host waits for these two lines before starting to capture.
print("READY")
time.sleep_ms(200)                       # small grace period for host to arm
print("START", SAMPLE_RATE, DURATION_S)

# ---------- Sample loop (deterministic period) ----------
t_next = time.ticks_us()
for _ in range(TOTAL_SAMPLES):
    while time.ticks_diff(time.ticks_us(), t_next) < 0:
        pass
    v = adc.read_u16()                   # 0–65535, matches Pico's rasp.py
    print(v)
    t_next = time.ticks_add(t_next, PERIOD_US)

print("END")
