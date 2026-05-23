# proj-emg

EMG (electromyography) hand-gesture classifier running on a Raspberry Pi Pico. A single ADC channel reads a muscle sensor, and a hardcoded decision tree classifies the signal in real time as **hand open** or **hand closed**.

## Hardware

- Raspberry Pi Pico (MicroPython firmware).
- EMG sensor wired to **GPIO26 (ADC0)**.
- Sampling rate: **500 Hz**.

## Repository layout

```
.
├── rasp.py            # Pico: data acquisition (labelled recording)
├── prediction.py      # Pico: real-time inference with embedded decision tree
├── rec_emg/           # 10 labelled recordings used to train the tree
├── old/               # Earlier iterations (5 kHz Timer variant, Arduino sketches,
│                      #   webcam + serial capture, plotting notebook)
├── requirements.txt   # Desktop-side Python deps (analysis / plotting only)
└── .venv/             # Local Python 3.12 environment
```

Files that import `machine`, `rp2`, or `utime` run **on the Pico**, not on the desktop.

## The two active scripts

### `rasp.py` — recording

Samples the ADC at 500 Hz for 30 seconds and writes a CSV (`Tempo(s),EMG_Value`) to the Pico's flash. Console prints timed prompts ("Feche a mão" / "Abra a mão") at 0, 5, 10, 15, 20, 25 s so the recording is time-labelled and can be cut into open/closed windows for training.

### `prediction.py` — inference

Same 500 Hz acquisition. Each 100-sample window (200 ms) is:

1. Smoothed with a 5-tap moving average.
2. Reduced to four features: **RMS, standard deviation, mean, waveform length**.
3. Fed into `prever_movimento(...)`, an inline if/else decision tree.
4. Printed as `Mão FECHADA` (1) or `Mão ABERTA` (0).

## How the model is updated

There is no model file — the decision tree is **pasted as Python code** inside `prever_movimento` in `prediction.py`. To retrain:

1. Record new sessions with `rasp.py` and copy them into `rec_emg/`.
2. Train a `DecisionTreeClassifier` (scikit-learn) externally on the four features above. *No training script is committed.*
3. Export the tree (`sklearn.tree.export_text` or equivalent if-else form) and replace the body of `prever_movimento`. Keep argument order `(rms, desvio_padrao, media, waveform_length)`.

If you change the window size, sampling rate, or filter in `prediction.py`, the existing thresholds become invalid and the tree must be retrained.

## Running

**On the Pico** — upload `rasp.py` or `prediction.py` as `main.py` using Thonny, `mpremote`, or `rshell`. No automated upload command is provided.

**On the desktop** — for ad-hoc plotting / analysis:

```bash
source .venv/bin/activate
python old/all_in/plot.py        # plots time-domain signal + FFT (expects emg_data.csv)
```

`requirements.txt` (numpy, pandas, matplotlib, opencv, pillow) is **desktop-only** and unrelated to what runs on the Pico.

## `old/` — what's in there

Kept for reference; not part of the current pipeline.

- `old/all_in/` — 5 kHz Timer-interrupt acquisition (`main.py`), FFT plot (`plot.py`), threaded serial + webcam recorder (`camTTL.py`), and an Arduino sketch.
- `old/highFreq/` — high-frequency experiments: Arduino with `TimerOne`, Pico PIO state machine, threaded PC reader. Documented frequency limits in its `readme.md`.
- `old/extra/` — original prototype code (Colab + Arduino).
- `old/Gráficos_do_sensor(emg).ipynb` — exploratory plotting notebook.
- `old/emg_data*.csv` — older recordings.

Sampling rates, file naming, and feature definitions differ between subdirectories — don't assume consistency with the root scripts.

## Status

| Component                    | State                                                  |
|------------------------------|--------------------------------------------------------|
| Pico acquisition (`rasp.py`) | Working, used to produce `rec_emg/*.csv`.              |
| Pico inference (`prediction.py`) | Working, decision tree hardcoded.                  |
| Trained model in repo        | None — only the inlined tree in `prediction.py`.        |
| Training script              | Not committed (done externally).                       |
| Tests / linter / CI          | None.                                                  |
| README / docs                | This file + `CLAUDE.md`.                               |
