"""Host-side recorder for the ESP32-S3 EMG streamer.

Reads samples streamed by ``esp32-board.py`` over USB-CDC and writes a CSV
matching the format produced by the Pico's ``rasp.py``:
``Tempo(s),EMG_Value``.

Prompts ("Feche a mão" / "Abra a mão") are shown to the operator at the
same times rasp.py uses, but the timing is driven from the host based on
sample count — keeps the on-device script simple and noise-free.

Usage:
    python esp32-pc.py --port /dev/ttyACM0 --out emg_1000hz_esp32_01.csv
"""

import argparse
import sys
import time

import serial

PROMPTS = [
    (0, "Manter o braço parado com a mão aberta"),
    (5, "Feche a mão"),
    (10, "Abra a mão"),
    (15, "Feche a mão"),
    (20, "Abra a mão"),
    (25, "Feche a mão"),
]


def _readline(ser):
    return ser.readline().decode("ascii", errors="ignore").strip()


def record(port, baud, out_path):
    ser = serial.Serial(port, baudrate=baud, timeout=2)

    # 1. wait for READY
    print(f"Waiting for ESP32 on {port}...", flush=True)
    while True:
        line = _readline(ser)
        if line == "READY":
            break
        if line:
            print(f"[esp32] {line}", file=sys.stderr)

    # 2. wait for START fs duration
    while True:
        line = _readline(ser)
        if line.startswith("START"):
            _, fs_str, dur_str = line.split()
            fs = int(fs_str)
            duration = int(dur_str)
            break

    print(f"Recording fs={fs} Hz for {duration} s -> {out_path}")
    print("(prompts will appear in real time)\n")

    # 3. stream samples, show prompts, write CSV
    next_prompt = 0
    sample_count = 0
    t_start_real = time.monotonic()
    with open(out_path, "w") as f:
        f.write("Tempo(s),EMG_Value\n")
        while True:
            line = _readline(ser)
            if not line:
                continue
            if line == "END":
                break
            try:
                value = int(line)
            except ValueError:
                print(f"[esp32] {line}", file=sys.stderr)
                continue
            elapsed = sample_count / fs
            f.write(f"{elapsed:.4f},{value}\n")
            sample_count += 1
            if next_prompt < len(PROMPTS) and elapsed >= PROMPTS[next_prompt][0]:
                t_prompt, msg = PROMPTS[next_prompt]
                print(f"[{t_prompt:>2}s] {msg}")
                next_prompt += 1

    real_dur = time.monotonic() - t_start_real
    expected = duration
    print()
    print(f"Done. {sample_count} samples written.")
    print(f"  expected duration: {expected:.1f} s")
    print(f"  real duration:     {real_dur:.1f} s")
    if abs(real_dur - expected) > 0.5:
        print("  ⚠ real duration differs from expected — check sampling jitter.")
    ser.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/ttyACM0",
                   help="ESP32-S3 USB-CDC serial port (default: /dev/ttyACM0)")
    p.add_argument("--baud", default=115200, type=int,
                   help="Baud rate. Ignored by USB-CDC but pyserial needs it.")
    p.add_argument("--out", default="emg_esp32.csv",
                   help="Output CSV path")
    args = p.parse_args()
    record(args.port, args.baud, args.out)


if __name__ == "__main__":
    main()
