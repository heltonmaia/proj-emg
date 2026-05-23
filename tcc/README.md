# `tcc/` — EMG filtering & spectral analysis

Student work derived from the project's EMG recordings. Originally a Jupyter
notebook (`cods_protese_emg.ipynb`); now also maintained as a runnable
Python script (`emg_filter_analysis.py`).

## Files

| File                          | What it is                                                            |
|-------------------------------|-----------------------------------------------------------------------|
| `emg_filter_analysis.py`      | Cleaned-up runnable version of the notebook (entry point).            |
| `cods_protese_emg.ipynb`      | Original notebook — kept for reference, not maintained going forward. |
| `new_emg_data8.csv`           | 500 Hz EMG recording used as input (a copy of `rec_emg/new_emg_data8.csv`). |
| `emg_1000hz_raw5.csv`         | 1000 Hz EMG recording (not yet used by the script — see notes below). |

## How to run

```bash
source ../.venv/bin/activate
python emg_filter_analysis.py
```

Requires `scipy` and `plotly` in addition to what was already in
`requirements.txt`; both were added in this iteration.

---

## Part 1 — Modifications

Changes applied while converting `cods_protese_emg.ipynb` to
`emg_filter_analysis.py`. Each entry is a correction or refactor; original
behaviour is preserved unless explicitly noted.

### Bug fixes

1. **Dead notch-filter lines removed.** The notebook assigned `signal_notch`
   three times in a row:

   ```python
   signal_notch = np.zeros_like(signal)                          # dead
   signal_notch = np.convolve(signal, b_notch, mode='same')      # dead
   signal_notch = filtfilt(b_notch, a_notch, signal)             # actual
   ```

   Only the last line had any effect. The first two were removed.

2. **Plotly Y-axis label fixed.** The original divided the FFT magnitude by
   `1e6` but labelled the axis `"Magnitude (x 10^6)"`. Dividing by 10⁶
   makes the displayed values smaller, so the correct label is
   `"Magnitude (× 10⁻⁶)"`. Updated both FFT plots.

3. **Stale variable references removed.** Comments mentioned
   `signal_filtered4` (a name that never existed in the notebook — likely a
   leftover from a previous version). Removed.

### Refactoring

4. **Single import block at the top.** Cells in the notebook re-imported
   `numpy`, `matplotlib`, `plotly`, and `scipy.signal` repeatedly; the
   script imports each module once.

5. **Script-relative path for the CSV.** The notebook used
   `pd.read_csv("new_emg_data8.csv")`, which only worked from the directory
   containing the CSV. The script now resolves the path via
   `os.path.dirname(__file__)`, so it runs from any working directory.

6. **FFT extracted into a function.** The notebook had two near-identical
   cells computing and plotting the FFT (one for filtered, one for raw).
   Both are now calls to a single `plot_fft(x, fs, title, y_range=None)`
   helper. The behaviour matches the second cell (which fixed the Y range
   for the raw-signal plot).

### Configuration

7. **Constants pulled to the top.** `fs`, `lowcut`, `highcut`, `notch_freq`,
   and `notch_Q` are grouped together so a student can change one value
   without scanning the file.

### Dependencies

8. **`requirements.txt` updated.** Added `scipy==1.17.1` and `plotly==6.7.0`,
   which the notebook used but never declared.

### Deliberately *not* changed

- **Two plotting backends.** The original uses matplotlib for the time-domain
  plot and Plotly for the FFT plots. We kept that split (the FFTs benefit
  from Plotly's interactive hover); revisit later if you want a single
  backend.
- **Filter parameters.** 60 Hz notch (Q=30), 20–240 Hz Butterworth band-pass,
  4th order, zero-phase via `filtfilt` / `sosfiltfilt`. Unchanged.

---

## Part 2 — Functionality and results

What the script does and what it produces, in order.

### Inputs

- A CSV with two columns: `Tempo(s)` (ignored, only used to verify sampling
  rate) and `EMG_Value` (raw 12-bit ADC counts, 0–4095, expanded into 16-bit
  via the Pico's `adc.read_u16()`).
- Sampling rate is hard-coded to `fs = 500` Hz, matching how
  `new_emg_data8.csv` was recorded by `rasp.py` at the project root.

### Pipeline

1. **Notch filter, 60 Hz.** `scipy.signal.iirnotch(60, Q=30, fs=500)` gives a
   2nd-order IIR notch. Applied via `filtfilt` (forward-backward) for zero
   phase distortion. Removes mains-frequency interference.

2. **Band-pass 20–240 Hz Butterworth, 4th order.** Built with
   `butter(4, [20, 240], btype="bandpass", fs=500, output="sos")` and applied
   via `sosfiltfilt`. The lower cutoff kills baseline drift and motion
   artifacts; the upper cutoff is just below Nyquist (250 Hz) and keeps the
   bulk of EMG energy (typically 20–150 Hz for surface EMG).

3. **Output: `signal_filtered`** — same length as the input, ready to feed
   into feature extraction (RMS / std / mean / waveform-length) in the next
   stage.

### Plots produced

| # | Plot                                             | Library    |
|---|--------------------------------------------------|------------|
| 1 | Time-domain: raw signal vs filtered signal       | matplotlib |
| 2 | FFT magnitude of the **filtered** signal, 0→Nyq. | plotly     |
| 3 | FFT magnitude of the **raw** signal, Y zoomed [0, 4] | plotly |

Plot 3 has the Y axis fixed to `[0, 4]` (after the `× 10⁻⁶` scaling) so the
60 Hz spike and harmonics are visible without being dwarfed by the DC and
very-low-frequency content.

### Expected results

- Plot 1: a much cleaner filtered signal with no slow drift and clear
  bursts where the hand closes.
- Plot 2 (filtered FFT): energy concentrated in 20–150 Hz with a near-zero
  notch around 60 Hz and a roll-off above ~200 Hz.
- Plot 3 (raw FFT): same general shape **plus** a tall spike at 60 Hz (and
  smaller harmonics at 120, 180 Hz) — that's exactly the interference the
  notch removes.

### Not yet implemented (next steps for the student)

- **Feature extraction.** The features used by `prediction.py` on the Pico
  (RMS, std-dev, mean, waveform length on 100-sample windows) are not
  computed here. Adding them is the natural next step before training a
  classifier offline.
- **`emg_1000hz_raw5.csv` is unused.** That recording was taken at 1000 Hz,
  not 500 Hz. To analyse it, set `fs = 1000` and re-evaluate filter
  parameters (`highcut` can go up to ~490 Hz before hitting Nyquist).
- **No classifier here.** The decision tree hardcoded in
  `../prediction.py` did *not* come from this notebook — it was trained
  elsewhere. If we want a reproducible training pipeline, that has to be
  added.
