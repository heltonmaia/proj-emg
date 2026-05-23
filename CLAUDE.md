# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

EMG (electromyography) hand-gesture classification on a Raspberry Pi Pico. A single ADC channel on GPIO26 samples a muscle sensor; a hardcoded decision tree decides "hand open" vs "hand closed" in real time. The README is one line ("# ECT-proj-emg") — there is no other prose documentation, so this file is the entry point.

Comments and console prompts in the code are in Portuguese.

## Two execution targets — don't confuse them

Code in this repo runs in two completely separate environments:

1. **On the Raspberry Pi Pico (MicroPython)** — any file that imports `machine`, `rp2`, or `utime`. These are not runnable on the desktop. Don't try to `pip install` their dependencies or execute them with the project `.venv`. They are flashed/uploaded to the Pico (typically as `main.py`).
   - `rasp.py` — data acquisition. Samples ADC at 500 Hz for 30 s and writes `new_emg_dataN.csv` on the Pico's flash. Prints timed prompts ("Feche a mão" / "Abra a mão") so the resulting CSV is labelled by time window.
   - `prediction.py` — real-time inference. Same 500 Hz sampling, 100-sample window (200 ms), 5-tap moving-average filter, then computes RMS / std / mean / waveform-length features and runs them through an inline `prever_movimento(...)` decision tree to print "Mão FECHADA" or "Mão ABERTA".
   - `old/main.py`, `old/all_in/main.py`, `old/highFreq/rasp-pico.py` — older Pico variants (notably `old/all_in/main.py` samples at 5 kHz via `Timer` interrupt with a 1000-sample buffer).

2. **On a desktop / laptop (CPython)** — analysis, plotting, video capture, serial acquisition. Uses `.venv/` (Python 3.12). `requirements.txt` (numpy, pandas, matplotlib, opencv, pillow) is for this side only.
   - `old/all_in/plot.py` — reads `emg_data.csv` and plots the time-domain signal plus FFT (assumes 5 kHz sampling, matching `old/all_in/main.py`).
   - `old/all_in/camTTL.py`, `old/modules/utils.py` (called from `old/main.py`) — webcam recording, threaded serial+video capture.
   - `old/highFreq/computer.py` — high-throughput threaded serial reader for the high-frequency Arduino/Pico variants.
   - `old/Gráficos_do_sensor(emg).ipynb` — exploratory plotting notebook.

`old/all_in/arduino/arduino.ino` and `old/highFreq/arduino.ino` are Arduino sketches (C++), flashed via Arduino IDE — a third target.

## How the trained model gets into the repo

There is no model file. The decision tree in `prediction.py` (`prever_movimento`) is hand-pasted source code — the output of an external scikit-learn training run over recordings in `rec_emg/` (the `new_emg_data*.csv` files produced by `rasp.py`). To retrain:

1. Record new sessions with `rasp.py` on the Pico, copy the resulting CSVs into `rec_emg/`.
2. Train a `DecisionTreeClassifier` externally (notebook / standalone script — there is no training script tracked here) on the four features RMS, std-dev, mean, waveform length.
3. Export the tree to Python (`sklearn.tree.export_text` or equivalent if-else form) and paste it over the body of `prever_movimento` in `prediction.py`. Keep the feature order `(rms, desvio_padrao, media, waveform_length)`.

If you make changes to `prediction.py`'s feature extraction (window size, sample rate, filter), the existing tree's thresholds become invalid and the model must be retrained.

## Commands

The Pico-side scripts are uploaded with whichever MicroPython tool the user prefers (Thonny, `mpremote`, `rshell`) — no upload command is automated in the repo.

For desktop scripts:

```bash
source .venv/bin/activate           # Python 3.12 env, already populated from requirements.txt
python old/all_in/plot.py           # expects emg_data.csv in CWD
```

There is no test suite, linter, formatter, or build step configured.

## Layout

- `rasp.py`, `prediction.py` — current Pico scripts (acquisition and inference).
- `rec_emg/` — read-only directory of labelled training recordings (`new_emg_data1.csv` … `new_emg_data10.csv`).
- `old/` — earlier iterations. Don't assume code here matches the conventions of the root scripts; sampling rates, file naming, and feature sets differ between subdirectories (`old/all_in` is the 5 kHz Timer variant, `old/highFreq` is the Arduino/PIO experiment). Keep edits scoped to the active root scripts unless asked.
- `requirements.txt`, `.venv/` — desktop analysis environment only.
