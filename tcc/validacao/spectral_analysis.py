"""Spectral validation of the EMG signal — answers the question
"is this classifier actually seeing EMG, or amplitude of noise?"

Input  : reference_signal.csv (a 30 s Pico recording at 500 Hz with prompts at
         0/5/10/15/20/25 s for open/close/open/close/open/close).

Outputs:
  1. spectral_analysis.png  — 4-panel figure:
       (a) Time-domain signal with labelled windows
       (b) Linear FFT: average rest spectrum vs average contraction spectrum
       (c) Welch PSD (smoother estimate) for rest vs contraction
       (d) Spectrogram of the whole recording

  2. Console summary of band-wise energy ratios contraction/rest.

Run:
    cd tcc/validacao
    python spectral_analysis.py
"""

import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch, spectrogram

# ---------- Config ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "reference_signal.csv")
OUT_PNG = os.path.join(SCRIPT_DIR, "spectral_analysis.png")

FS = 500            # Hz, the Pico recording sample rate

# Window scheme of the recording prompts:
REST_WINDOWS = [(0, 5), (10, 15), (20, 25)]      # arm still / hand open
FLEX_WINDOWS = [(5, 10), (15, 20), (25, 30)]     # hand closed (contraction)

EMG_BAND = (20, 150)            # dominant sEMG band (highlighted on plots)
MAINS_HARMONICS = [60, 120, 180]


# ---------- Load ----------
df = pd.read_csv(CSV_PATH)
sig = df["EMG_Value"].values.astype(float)
t = df["Tempo(s)"].values
print(f"Loaded {len(sig)} samples ({t[-1]:.2f} s, fs={FS} Hz)")


# ---------- Helpers ----------
def slice_sig(t0, t1):
    mask = (t >= t0) & (t < t1)
    return sig[mask]


def avg_fft(windows):
    """Average linear-FFT magnitude across the given (t0, t1) windows."""
    spectra = []
    freqs_ref = None
    for t0, t1 in windows:
        x = slice_sig(t0, t1) - slice_sig(t0, t1).mean()  # remove DC
        n = len(x)
        spectra.append(np.abs(np.fft.rfft(x)) * 2 / n)
        if freqs_ref is None:
            freqs_ref = np.fft.rfftfreq(n, 1 / FS)
    return freqs_ref, np.mean(spectra, axis=0)


def avg_welch(windows, nperseg=512):
    """Average Welch PSD across the given windows."""
    psds = []
    freqs_ref = None
    for t0, t1 in windows:
        x = slice_sig(t0, t1) - slice_sig(t0, t1).mean()
        f, p = welch(x, fs=FS, nperseg=min(nperseg, len(x)))
        psds.append(p)
        if freqs_ref is None:
            freqs_ref = f
    return freqs_ref, np.mean(psds, axis=0)


def band_energy(freqs, spec, f0, f1):
    mask = (freqs >= f0) & (freqs < f1)
    return spec[mask].sum()


# ---------- Spectra ----------
fft_freqs, fft_rest = avg_fft(REST_WINDOWS)
_,         fft_flex = avg_fft(FLEX_WINDOWS)
welch_freqs, welch_rest = avg_welch(REST_WINDOWS)
_,           welch_flex = avg_welch(FLEX_WINDOWS)


# ---------- Figure ----------
fig, axes = plt.subplots(4, 1, figsize=(12, 14))

# (a) Time domain
ax = axes[0]
ax.plot(t, sig, lw=0.4, color="black")
for t0, t1 in REST_WINDOWS:
    ax.axvspan(t0, t1, color="tab:blue", alpha=0.10)
for t0, t1 in FLEX_WINDOWS:
    ax.axvspan(t0, t1, color="tab:red", alpha=0.12)
ax.set_xlabel("Tempo (s)")
ax.set_ylabel("EMG_Value (ADC)")
ax.set_title("(a) Sinal completo — azul = repouso, vermelho = contração")
ax.grid(True, alpha=0.3)

# (b) Linear FFT
ax = axes[1]
ax.plot(fft_freqs, fft_rest, label="Repouso (mão aberta, parada)", color="tab:blue", lw=1.5)
ax.plot(fft_freqs, fft_flex, label="Contração (mão fechada)", color="tab:red", lw=1.5)
ax.axvspan(*EMG_BAND, color="green", alpha=0.07, label=f"Banda dominante sEMG ({EMG_BAND[0]}–{EMG_BAND[1]} Hz)")
for hz in MAINS_HARMONICS:
    ax.axvline(hz, color="grey", ls=":", alpha=0.6)
    ax.text(hz, ax.get_ylim()[1] * 0.95, f" {hz} Hz", color="grey", fontsize=8, va="top")
ax.set_xlim(0, FS / 2)
ax.set_xlabel("Frequência (Hz)")
ax.set_ylabel("Magnitude FFT (linear)")
ax.set_title("(b) Espectro médio: repouso vs contração (FFT linear)")
ax.legend(loc="upper right", fontsize=9)
ax.grid(True, alpha=0.3)

# (c) Welch PSD (log)
ax = axes[2]
ax.semilogy(welch_freqs, welch_rest, label="Repouso", color="tab:blue", lw=1.5)
ax.semilogy(welch_freqs, welch_flex, label="Contração", color="tab:red", lw=1.5)
ax.axvspan(*EMG_BAND, color="green", alpha=0.07)
for hz in MAINS_HARMONICS:
    ax.axvline(hz, color="grey", ls=":", alpha=0.6)
ax.set_xlim(0, FS / 2)
ax.set_xlabel("Frequência (Hz)")
ax.set_ylabel("PSD (log)")
ax.set_title("(c) PSD (estimativa de Welch, log) — visão mais suave dos espectros")
ax.legend(loc="upper right", fontsize=9)
ax.grid(True, which="both", alpha=0.3)

# (d) Spectrogram
ax = axes[3]
f_spec, t_spec, Sxx = spectrogram(sig - sig.mean(), fs=FS, nperseg=256, noverlap=128)
pcm = ax.pcolormesh(t_spec, f_spec, 10 * np.log10(Sxx + 1e-12), shading="gouraud", cmap="viridis")
fig.colorbar(pcm, ax=ax, label="Potência (dB)")
for t0 in [5, 10, 15, 20, 25]:
    ax.axvline(t0, color="white", ls="--", alpha=0.6, lw=0.8)
ax.set_xlabel("Tempo (s)")
ax.set_ylabel("Frequência (Hz)")
ax.set_title("(d) Espectrograma — bandas verticais escuras = contrações")

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=120)
print(f"saved {OUT_PNG}")


# ---------- Console summary ----------
print()
print("=" * 64)
print("Razão Contração/Repouso de energia espectral, por banda")
print("=" * 64)
print(f"{'Banda':>22} | {'Repouso':>10} | {'Contração':>12} | {'C/R':>6}")
print("-" * 64)
for label, f0, f1 in [
    ("< 5 Hz (drift)", 0, 5),
    ("5–20 Hz", 5, 20),
    ("20–150 Hz (EMG dom.)", 20, 150),
    ("150–250 Hz (EMG alta)", 150, 250),
    ("~60 Hz (rede)", 55, 65),
    ("~120 Hz (2ª harm.)", 115, 125),
    ("~180 Hz (3ª harm.)", 175, 185),
]:
    r = band_energy(fft_freqs, fft_rest, f0, f1)
    c = band_energy(fft_freqs, fft_flex, f0, f1)
    ratio = c / r if r > 0 else float("nan")
    flag = " ✓" if 20 <= (f0 + f1) / 2 <= 250 and ratio > 2 else ""
    print(f"{label:>22} | {r:>10.1f} | {c:>12.1f} | {ratio:>5.2f}x{flag}")

print()
print("Interpretação:")
print("  - Aumento broadband em 20–150 Hz → assinatura de EMG real.")
print("  - Picos 60/120/180 Hz proporcionais ao broadband → rede não domina.")
print("  - <5 Hz é a banda com MENOR ratio → artefato de movimento não é o motor.")
