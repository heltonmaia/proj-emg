# `esp32-s3/` — EMG acquisition on ESP32-S3 (1000 Hz)

Scripts for streaming EMG samples from an ESP32-S3 to a host laptop over
USB-CDC, then writing them as a CSV in the same format produced by the
Pico's `rasp.py`.

This is the **new acquisition path** for the project (replacing the
Raspberry Pi Pico / 500 Hz setup). See the migration notes in the project
root `README.md`.

## The two scripts run on different machines

```
   [EMG sensor] -- analog --> [ESP32-S3] === USB cable === > [laptop]
                                  ▲                              ▲
                                  │                              │
                           esp32-board.py                  esp32-pc.py
                          (firmware, MicroPython,        (host, CPython,
                           runs on the board)             runs in .venv)
                                  │                              │
                           reads ADC,                     reads serial,
                           prints samples                 writes CSV file
                           over USB-CDC                   to laptop disk
```

The ESP32-S3 has no way to write to your laptop's filesystem — it can only
push bytes down the USB cable. `esp32-pc.py` is what catches those
bytes and saves the CSV.

## Files

| File              | Runs on   | Role                                          |
|-------------------|-----------|-----------------------------------------------|
| `esp32-board.py`   | ESP32-S3  | Flash as `main.py`. Streams samples at 1 kHz. |
| `esp32-pc.py` | Laptop    | Reads serial, writes `Tempo(s),EMG_Value` CSV. |

## How to use

Prerequisites: MicroPython flashed on the ESP32-S3, `mpremote` installed on
the host, project `.venv` activated (provides `pyserial`).

```bash
# 1. Upload firmware to the board
mpremote cp esp32-s3/esp32-board.py :main.py

# 2. Reset/reconnect the board, then run the host recorder
source .venv/bin/activate
python esp32-s3/esp32-pc.py --port /dev/ttyACM0 --out recording_01.csv
```

The host prints the same prompts as the Pico's `rasp.py` ("Feche a mão" /
"Abra a mão") at 0, 5, 10, 15, 20, 25 s. The CSV format matches Pico
recordings byte-for-byte, so the offline analysis scripts in `tcc/` work
without modification.

## Why USB-CDC and not Wi-Fi / BLE / SD card

| Option                       | Issue                                                 |
|------------------------------|--------------------------------------------------------|
| Wi-Fi / BLE streaming        | RF noise injected into the ADC — defeats the platform. |
| SD card                       | Board doesn't have one; would burn a pin and money.    |
| Internal flash (LittleFS)    | Wears flash on repeated writes; extra step to download.|
| **USB-CDC stream → host CSV** | **Clean ADC, no storage to manage, megabyte/s headroom.**|

`esp32-board.py` also explicitly disables Wi-Fi and BLE before sampling
(both run on the same radio block that couples into the ADC).

## Why ADC1 only

The ESP32 family has two ADC peripherals. **ADC2 is shared with the Wi-Fi
radio** and reads are unreliable whenever Wi-Fi is active. ADC1 is
independent and safe. `esp32-board.py` is wired to GPIO1 (= ADC1_CH0); if
you move the input pin, keep it on an ADC1 channel (GPIO1–GPIO10 on the
S3).

## Headroom at 1 kHz

A 1 kHz sample period is 1000 µs. Per-sample work on the S3 in MicroPython:

| Step                                | Cost     |
|-------------------------------------|----------|
| `adc.read_u16()`                    | ~30–50 µs |
| `print(value)` (int → str → USB-CDC) | ~100–200 µs |
| Loop + busy-wait                    | ~10 µs |
| **Total**                           | **~150–250 µs** |

~75 % idle per cycle — plenty of room to bump to 2 kHz or add on-device
filtering later.
