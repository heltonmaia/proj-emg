"""Host-side recorder for the ESP32-C5 EMG streamer.

The board (`esp32-board.py`) streams raw samples continuously, with no
handshake. This script:

  1. Opens the serial port.
  2. Drains whatever was already buffered (so we start fresh).
  3. Reads exactly ``DURATION_S * FS`` samples, writing each one as a
     CSV row with computed timestamp.
  4. Shows the same prompts ("Feche a mão" / "Abra a mão") at the same
     times that the Pico's ``rasp.py`` uses, so labelled training data
     can be cut out of the recording.

CSV format matches the Pico's ``rasp.py`` output:
``Tempo(s),EMG_Value``.

Usage:
    python esp32-pc.py --port /dev/ttyACM0 --out emg_1000hz_esp32_01.csv
"""

import argparse
import sys
import time

import serial

FS = 2000
DURATION_S = 30
TOTAL_SAMPLES = FS * DURATION_S

PROMPTS = [
    (0, "Manter o braço parado com a mão aberta"),
    (5, "Feche a mão"),
    (10, "Abra a mão"),
    (15, "Feche a mão"),
    (20, "Abra a mão"),
    (25, "Feche a mão"),
]


def record(port, baud, out_path):
    ser = serial.Serial(port, baudrate=baud, timeout=2)
    print(f"Opened {port}. Draining stale data...", flush=True)
    time.sleep(0.3)                       # let USB-CDC settle
    ser.reset_input_buffer()

    print(f"Recording fs={FS} Hz for {DURATION_S} s -> {out_path}")
    print("(prompts will appear in real time)\n")

    sample_count = 0
    next_prompt = 0
    t_start = time.monotonic()

    with open(out_path, "w") as f:
        f.write("Tempo(s),EMG_Value\n")
        while sample_count < TOTAL_SAMPLES:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if not line:
                continue
            try:
                value = int(line)
            except ValueError:
                # Non-numeric (REPL prompt, error message, etc.) — print and skip.
                print(f"[esp32] {line}", file=sys.stderr)
                continue
            elapsed = sample_count / FS
            f.write(f"{elapsed:.4f},{value}\n")
            sample_count += 1
            if next_prompt < len(PROMPTS) and elapsed >= PROMPTS[next_prompt][0]:
                t_prompt, msg = PROMPTS[next_prompt]
                print(f"[{t_prompt:>2}s] {msg}")
                next_prompt += 1

    real_dur = time.monotonic() - t_start
    print()
    print(f"Done. {sample_count} samples written.")
    print(f"  expected duration: {DURATION_S:.1f} s")
    print(f"  real duration:     {real_dur:.1f} s")
    if abs(real_dur - DURATION_S) > 0.5:
        print("  ⚠ real duration differs from expected — check sampling jitter.")
    ser.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/ttyACM0",
                   help="ESP32-C5 USB-CDC serial port (default: /dev/ttyACM0)")
    p.add_argument("--baud", default=115200, type=int,
                   help="Baud rate. Ignored by USB-CDC but pyserial needs it.")
    p.add_argument("--out", default="emg_esp32.csv",
                   help="Output CSV path")
    args = p.parse_args()
    record(args.port, args.baud, args.out)


if __name__ == "__main__":
    main()
