# `esp32-c5/` — EMG acquisition on ESP32-C5 (2000 Hz)

Scripts for streaming EMG samples from an ESP32-C5 to a host laptop over
USB-CDC, then writing them as a CSV in the same format produced by the
Pico's `rasp.py`.

This is the **new acquisition path** for the project (replacing the
Raspberry Pi Pico / 500 Hz setup). See the migration notes in the project
root `README.md`.

> **Why C5 and not S3?** We initially scoped this for the ESP32-S3, but the
> board on hand turned out to be an ESP32-C5 (RISC-V single-core,
> Wi-Fi 6 + BLE 5 + 802.15.4, FPU @ 240 MHz). For the EMG pipeline the two
> chips are functionally equivalent (both have FPU, native USB-CDC, and
> enough headroom for 2 kHz sampling + on-device IIR filtering). MicroPython
> v1.28.0 (Apr 2026) has stable C5 support.

## Hardware wiring

The sensor in use is the Brazilian-market **"Módulo Sensor Elétrico
Muscular EMG Raw"** — a raw-output instrumentation amplifier (likely
AD620 / INA126) on a red PCB, with a 5-pin header
(`+Vs`, `GND`, `-Vs`, `SIG`, `GND`) and a 3.5 mm TRS jack for the
electrodes. It needs a **split ±9 V supply**, typically from two
9 V batteries in series.

### The single most important concept: common ground

The ADC measures voltage **between SIG and the C5's own GND**. If SIG is
electrically floating relative to that GND, the reading is undefined and
can even damage the input. Everything in the circuit needs to share the
same 0 V reference.

For a split supply, **the 0 V reference is not the negative terminal of
a battery** — it's the **center tap**, the point where the two batteries
meet:

```
                   ┌── +9 V  → module +Vs
   Battery 1 ──────┤
                   │
                   ├── 0 V (CENTER TAP) ◄── system ground reference
                   │
   Battery 2 ──────┤
                   └── -9 V  → module -Vs
```

`+9 V` sits **9 V above** this reference; `-9 V` sits **9 V below** it.
The module's `GND` pins (there are two of them on the header, internally
the same node) are tied to this center tap. **The C5's GND must be tied
to the same center tap**, so that the C5 ADC and the sensor SIG share
the same 0 V.

### Connection table

| From | To | Why |
|---|---|---|
| Battery 1 (+) | Module `+Vs` | positive rail |
| Battery 1 (–) ⟵ joined ⟶ Battery 2 (+) | Module `GND` (between +Vs/-Vs) | **center tap = 0 V reference** |
| Battery 2 (–) | Module `-Vs` | negative rail |
| Module **`SIG`** | **C5 GPIO1** | analog EMG signal → ADC1_CH0 |
| Module **`GND`** (next to SIG) | **C5 GND** | common ground tie (mandatory) |

The two GND pins on the module are the same electrical node — use
whichever is convenient. In the existing Pico setup, the "battery-side"
GND goes to the center tap and the "signal-side" GND goes to the MCU.
Replicate that for the C5.

### Symptoms of a missing ground tie

If the module-GND-to-C5-GND wire is missing or loose, you'll see one of:
constant ADC value, full-scale saturation (0 or 65 535), no response to
muscle contraction, lots of 60 Hz coupled noise — or, in the worst case,
permanent damage to the GPIO pin from current through its ESD diodes.

### ADC pin choice

The ESP32-C5 has a **single 12-bit SAR ADC** with up to 6 channels on
GPIO1–GPIO6 (datasheet Table 2-7). Unlike older ESP32 chips, there is
**no second ADC unit shared with the Wi-Fi radio**, so the classic
"ADC1 only" caveat does not apply here.

| GPIO  | ADC channel | Notes                                  |
|-------|-------------|----------------------------------------|
| GPIO1 | ADC1_CH0    | What we use. Not a strap pin.          |
| GPIO2 | ADC1_CH1    | Strap pin — avoid for analog input.    |
| GPIO3 | ADC1_CH2    | Strap pin — avoid for analog input.    |
| GPIO4 | ADC1_CH3    | OK                                     |
| GPIO5 | ADC1_CH4    | OK                                     |
| GPIO6 | ADC1_CH5    | OK                                     |

If you change the pin in `esp32-board.py`, keep it on one of GPIO4–GPIO6
(or GPIO1) to avoid strapping conflicts.

## The two scripts run on different machines

```
   [EMG sensor] -- analog --> [ESP32-C5] === USB cable === > [laptop]
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

The ESP32-C5 has no way to write to your laptop's filesystem — it can only
push bytes down the USB cable. `esp32-pc.py` is what catches those
bytes and saves the CSV.

## Files

| File              | Runs on   | Role                                          |
|-------------------|-----------|-----------------------------------------------|
| `esp32-board.py`   | ESP32-C5  | Flash as `main.py`. Streams samples at 2 kHz. |
| `esp32-pc.py` | Laptop    | Reads serial, writes `Tempo(s),EMG_Value` CSV. |

## How to use

### One-time setup — flash MicroPython

```bash
source .venv/bin/activate
.venv/bin/python -m esptool --port /dev/ttyACM0 --chip esp32c5 erase-flash
.venv/bin/python -m esptool --port /dev/ttyACM0 --chip esp32c5 \
    write-flash 0x2000 ESP32_GENERIC_C5-<date>-<version>.bin
```

> ⚠ The ESP32-C5 flash offset is **`0x2000`**, *not* `0x0` like the C3/C6
> or `0x1000` like the original ESP32/S2/S3. Flashing at the wrong offset
> leaves the chip in a panic-reboot loop (looks like a flaky cable but
> isn't). Per the micropython.org installation page.

Firmware: <https://micropython.org/download/ESP32_GENERIC_C5/> — we tested
with v1.28.0 (2026-04-06).

### Upload the streamer + record

```bash
# 1. Upload the on-device script as main.py
mpremote cp esp32-c5/esp32-board.py :main.py

# 2. Replug the board so main.py runs (mpremote cp does NOT auto-reset).

# 3. Record (host)
source .venv/bin/activate
python esp32-c5/esp32-pc.py --port /dev/ttyACM0 --out recording_01.csv
```

The host prints the same prompts as the Pico's `rasp.py` ("Feche a mão" /
"Abra a mão") at 0, 5, 10, 15, 20, 25 s. The CSV format matches Pico
recordings byte-for-byte, so the offline analysis scripts in `tcc/` work
without modification.

## Protocol — no handshake

The board does **not** wait for the host before streaming. After a
2-second boot grace (during which `mpremote` can interrupt for
re-flashing), it enters an infinite `while True:` loop printing one ADC
value per millisecond. The host opens the serial port whenever it wants,
calls `ser.reset_input_buffer()` to drop any stale buffered data, then
reads exactly `DURATION_S × FS` samples (30 000 by default) and stops.
The board keeps streaming after the host disconnects — MicroPython's
USB-CDC drops bytes silently when no host is reading, so no harm done.

We tried a bidirectional `READY` / `START` handshake first; it didn't
work reliably on the C5 (board got stuck in `sys.stdin.buffer.read(1)`
even after the host wrote a byte). The no-handshake stream is the only
pattern we've found that's robust on this chip + MicroPython version.

## Why USB-CDC and not Wi-Fi / BLE / SD card

| Option                       | Issue                                                 |
|------------------------------|--------------------------------------------------------|
| Wi-Fi / BLE streaming        | RF noise injected into the ADC — defeats the platform. |
| SD card                       | Board doesn't have one; would burn a pin and money.    |
| Internal flash (LittleFS)    | Wears flash on repeated writes; extra step to download.|
| **USB-CDC stream → host CSV** | **Clean ADC, no storage to manage, megabyte/s headroom.**|

`esp32-board.py` also explicitly disables Wi-Fi and BLE before sampling
(both share the radio block, which couples into the analog frontend).

## Headroom at 2 kHz

A 2 kHz sample period is 500 µs. Per-sample work on the C5 in MicroPython:

| Step                                | Cost     |
|-------------------------------------|----------|
| `adc.read_u16()`                    | ~30–50 µs |
| `print(value)` (int → str → USB-CDC) | ~100–200 µs |
| Loop + busy-wait                    | ~10 µs |
| **Total**                           | **~150–250 µs** |

50–70 % idle per cycle at 2 kHz. Validated empirically: 20 000 samples
written in exactly 10.0 s of real time (zero jitter). Going higher (4 kHz)
would start eating into safety margin — keep at 2 kHz unless you have a
specific reason to push it.
