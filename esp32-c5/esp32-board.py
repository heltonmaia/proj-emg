"""MicroPython script for ESP32-C5 — streams raw EMG samples via USB-CDC.

Flash this to the ESP32-C5 as ``main.py``. It reads one ADC channel at
SAMPLE_RATE Hz and prints each sample as a line on the native USB serial
port, forever.

No handshake: the host (``esp32-pc.py``) attaches whenever it wants,
discards any stale buffered data, and then counts the next N samples
to capture a fixed-duration recording. The board keeps streaming after
the host disconnects — that's fine, MicroPython's USB-CDC drops bytes
silently when no host is reading.

Wi-Fi and BLE are disabled before sampling to keep the ADC quiet.

A 2-second sleep at boot gives a window for ``mpremote`` to interrupt
the script for re-flashing (Ctrl-C reaches the board reliably during
sleeps; once in the busy sample loop it's less reliable).
"""

import time
from machine import ADC, Pin

# ---------- Config ----------
SAMPLE_RATE = 1000                       # Hz
ADC_PIN = 1                              # GPIO1 = ADC1_CH0 (C5 has a single ADC unit)
PERIOD_US = 1_000_000 // SAMPLE_RATE

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

# ---------- Grace period for mpremote to interrupt if re-flashing ----------
time.sleep(2)

# ---------- ADC ----------
adc = ADC(Pin(ADC_PIN), atten=ADC.ATTN_11DB)   # ~0–3.3 V input range

# ---------- Continuous streaming ----------
t_next = time.ticks_us()
while True:
    while time.ticks_diff(time.ticks_us(), t_next) < 0:
        pass
    print(adc.read_u16())                # 0–65535
    t_next = time.ticks_add(t_next, PERIOD_US)
