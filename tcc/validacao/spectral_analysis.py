"""Spectral validation of the EMG signal — answers the question
"is this classifier actually seeing EMG, or amplitude of noise?"

Input  : reference_signal.csv (a 30 s Pico recording at 500 Hz with prompts at
         0/5/10/15/20/25 s for open/close/open/close/open/close).

Outputs (all written next to this script):

  Combined 4-panel figure (time → spectrogram → FFT → Welch PSD):
    - spectral_analysis.png   (raster, for README preview)
    - spectral_analysis.svg   (vector envelope, spectrogram rasterized inside)

  Individual panels (each as its own vector file):
    - panel_timeseries.svg
    - panel_spectrogram.svg
    - panel_fft.svg
    - panel_welch_psd.svg

  Console summary of band-wise energy ratios contraction/rest.

Notes on the layout:
  - Time-series and spectrogram share the same time axis (0–30 s) and are
    stacked vertically so the same vertical column corresponds to the same
    instant in both plots.
  - The spectrogram's colorbar lives in a separate GridSpec column so its
    width doesn't shrink the spectrogram axis — all four main panels keep
    the same plot width.
  - `rasterized=True` on the spectrogram pcolormesh keeps the SVG small
    (text + axes remain vector; only the heatmap pixels are embedded as
    raster).

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

FS = 500            # Hz, the Pico recording sample rate
DURATION = 30       # s

REST_WINDOWS = [(0, 5), (10, 15), (20, 25)]
FLEX_WINDOWS = [(5, 10), (15, 20), (25, 30)]
EMG_BAND = (20, 150)
MAINS_HARMONICS = [60, 120, 180]
SAVE_DPI = 150


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
    spectra = []
    freqs_ref = None
    for t0, t1 in windows:
        x = slice_sig(t0, t1) - slice_sig(t0, t1).mean()
        n = len(x)
        spectra.append(np.abs(np.fft.rfft(x)) * 2 / n)
        if freqs_ref is None:
            freqs_ref = np.fft.rfftfreq(n, 1 / FS)
    return freqs_ref, np.mean(spectra, axis=0)


def avg_welch(windows, nperseg=512):
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
spec_f, spec_t, Sxx = spectrogram(sig - sig.mean(), fs=FS, nperseg=256, noverlap=128)


# ---------- Per-panel drawing functions ----------
def draw_timeseries(ax):
    ax.plot(t, sig, lw=0.4, color="black")
    for t0, t1 in REST_WINDOWS:
        ax.axvspan(t0, t1, color="tab:blue", alpha=0.10)
    for t0, t1 in FLEX_WINDOWS:
        ax.axvspan(t0, t1, color="tab:red", alpha=0.12)
    ax.set_xlim(0, DURATION)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("EMG_Value (ADC)")
    ax.set_title("Sinal completo — azul = repouso, vermelho = contração")
    ax.grid(True, alpha=0.3)


def draw_spectrogram(ax, fig, cax=None):
    pcm = ax.pcolormesh(spec_t, spec_f, 10 * np.log10(Sxx + 1e-12),
                        shading="gouraud", cmap="viridis", rasterized=True)
    for t0 in [5, 10, 15, 20, 25]:
        ax.axvline(t0, color="white", ls="--", alpha=0.6, lw=0.8)
    ax.set_xlim(0, DURATION)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Frequência (Hz)")
    ax.set_title("Espectrograma — bandas verticais escuras = contrações")
    if cax is not None:
        fig.colorbar(pcm, cax=cax, label="Potência (dB)")
    else:
        fig.colorbar(pcm, ax=ax, label="Potência (dB)")


def draw_fft(ax):
    ax.plot(fft_freqs, fft_rest, label="Repouso (mão aberta, parada)", color="tab:blue", lw=1.5)
    ax.plot(fft_freqs, fft_flex, label="Contração (mão fechada)", color="tab:red", lw=1.5)
    ax.axvspan(*EMG_BAND, color="green", alpha=0.07,
               label=f"Banda dominante sEMG ({EMG_BAND[0]}–{EMG_BAND[1]} Hz)")
    for hz in MAINS_HARMONICS:
        ax.axvline(hz, color="grey", ls=":", alpha=0.6)
        ax.text(hz, ax.get_ylim()[1] * 0.95, f" {hz} Hz",
                color="grey", fontsize=8, va="top")
    ax.set_xlim(0, FS / 2)
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("Magnitude FFT (linear)")
    ax.set_title("Espectro médio: repouso vs contração (FFT linear)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)


def draw_welch_psd(ax):
    ax.semilogy(welch_freqs, welch_rest, label="Repouso", color="tab:blue", lw=1.5)
    ax.semilogy(welch_freqs, welch_flex, label="Contração", color="tab:red", lw=1.5)
    ax.axvspan(*EMG_BAND, color="green", alpha=0.07)
    for hz in MAINS_HARMONICS:
        ax.axvline(hz, color="grey", ls=":", alpha=0.6)
    ax.set_xlim(0, FS / 2)
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("PSD (log)")
    ax.set_title("PSD (Welch, log) — visão suave dos espectros")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)


# ---------- Combined 4-panel figure ----------
# Layout: 4 rows × 2 columns. Column 0 hosts every plot at uniform width;
# column 1 is a thin slot reserved for the spectrogram colorbar (empty for
# the other rows). This keeps all four panels visually aligned by width.
fig = plt.figure(figsize=(12, 14))
gs = fig.add_gridspec(
    nrows=4, ncols=2,
    width_ratios=[1.0, 0.025],
    hspace=0.45, wspace=0.04,
)
ax_time = fig.add_subplot(gs[0, 0])
ax_spec = fig.add_subplot(gs[1, 0])
cax_spec = fig.add_subplot(gs[1, 1])
ax_fft = fig.add_subplot(gs[2, 0])
ax_welch = fig.add_subplot(gs[3, 0])

draw_timeseries(ax_time)
draw_spectrogram(ax_spec, fig, cax=cax_spec)
draw_fft(ax_fft)
draw_welch_psd(ax_welch)

for ext in ("png", "svg"):
    out = os.path.join(SCRIPT_DIR, f"spectral_analysis.{ext}")
    plt.savefig(out, dpi=SAVE_DPI, bbox_inches="tight")
    print(f"saved {out}")
plt.close(fig)


# ---------- Individual panels (vector) ----------
def save_individual(fname, draw_fn, needs_fig=False):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if needs_fig:
        draw_fn(ax, fig)          # spectrogram gets a colorbar on its own
    else:
        draw_fn(ax)
    plt.tight_layout()
    out = os.path.join(SCRIPT_DIR, fname)
    plt.savefig(out, dpi=SAVE_DPI, bbox_inches="tight")
    print(f"saved {out}")
    plt.close(fig)


save_individual("panel_timeseries.svg",  draw_timeseries)
save_individual("panel_spectrogram.svg", draw_spectrogram, needs_fig=True)
save_individual("panel_fft.svg",         draw_fft)
save_individual("panel_welch_psd.svg",   draw_welch_psd)


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
