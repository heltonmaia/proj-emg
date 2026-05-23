"""Spectral validation of the EMG signal — answers the question
"is this classifier actually seeing EMG, or amplitude of noise?"

Runs the same analysis on both reference recordings:

  reference_signal_500hz.csv    Pico, 500 Hz, columns: Tempo(s), EMG_Value
  reference_signal_1000hz.csv   1000 Hz, columns: EMG_Value only (time
                                synthesized from sample index)

Both recordings are assumed to follow the same 30-second prompt protocol:
  0s open/still, 5s close, 10s open, 15s close, 20s open, 25s close.

For each recording the script writes outputs into a subfolder named
after the sample rate (e.g. ``500hz/``, ``1000hz/``):

  <fs>hz/spectral_analysis.{png,svg}    Combined 4-panel figure
  <fs>hz/panel_timeseries.svg           Individual panels (vector)
  <fs>hz/panel_spectrogram.svg
  <fs>hz/panel_fft.svg
  <fs>hz/panel_welch_psd.svg

  A console summary of contraction/rest energy ratios per band.

A final comparison table is printed at the end.

Notes:
  - rasterized=True on the spectrogram pcolormesh keeps SVG sizes small
    (axes/text stay vector, only the heatmap is embedded as raster).
  - Time-series and spectrogram share a single x-axis (0–30 s) and the
    spectrogram's colorbar lives in a reserved GridSpec column so all
    panels keep the same plot width.

Run:
    cd tcc/validacao
    python spectral_analysis.py
"""

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch, spectrogram

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DURATION = 30
REST_WINDOWS = [(0, 5), (10, 15), (20, 25)]
FLEX_WINDOWS = [(5, 10), (15, 20), (25, 30)]
EMG_BAND = (20, 150)
MAINS_HARMONICS = [60, 120, 180]
SAVE_DPI = 150


@dataclass
class Dataset:
    label: str            # e.g. "500hz"
    csv: str
    fs: int


DATASETS = [
    Dataset(label="500hz",  csv="reference_signal_500hz.csv",  fs=500),
    Dataset(label="1000hz", csv="reference_signal_1000hz.csv", fs=1000),
]


# ---------- Per-dataset analysis ----------
def load(ds: Dataset):
    df = pd.read_csv(os.path.join(SCRIPT_DIR, ds.csv))
    sig = df["EMG_Value"].values.astype(float)
    if "Tempo(s)" in df.columns:
        t = df["Tempo(s)"].values
    else:
        t = np.arange(len(sig)) / ds.fs
    return sig, t


def slice_sig(sig, t, t0, t1):
    mask = (t >= t0) & (t < t1)
    return sig[mask]


def avg_fft(sig, t, windows, fs):
    spectra, freqs_ref = [], None
    for t0, t1 in windows:
        x = slice_sig(sig, t, t0, t1)
        x = x - x.mean()
        n = len(x)
        spectra.append(np.abs(np.fft.rfft(x)) * 2 / n)
        if freqs_ref is None:
            freqs_ref = np.fft.rfftfreq(n, 1 / fs)
    return freqs_ref, np.mean(spectra, axis=0)


def avg_welch(sig, t, windows, fs, nperseg=1024):
    psds, freqs_ref = [], None
    for t0, t1 in windows:
        x = slice_sig(sig, t, t0, t1)
        x = x - x.mean()
        f, p = welch(x, fs=fs, nperseg=min(nperseg, len(x)))
        psds.append(p)
        if freqs_ref is None:
            freqs_ref = f
    return freqs_ref, np.mean(psds, axis=0)


def band_energy(freqs, spec, f0, f1):
    return spec[(freqs >= f0) & (freqs < f1)].sum()


# ---------- Drawing functions (closures over per-dataset arrays) ----------
def make_drawers(ds: Dataset, sig, t, fft_freqs, fft_rest, fft_flex,
                 welch_freqs, welch_rest, welch_flex, spec_f, spec_t, Sxx):

    def draw_timeseries(ax):
        ax.plot(t, sig, lw=0.4, color="black")
        for t0, t1 in REST_WINDOWS:
            ax.axvspan(t0, t1, color="tab:blue", alpha=0.10)
        for t0, t1 in FLEX_WINDOWS:
            ax.axvspan(t0, t1, color="tab:red", alpha=0.12)
        ax.set_xlim(0, DURATION)
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("EMG_Value (ADC)")
        ax.set_title(f"Sinal completo ({ds.fs} Hz) — azul = repouso, vermelho = contração")
        ax.grid(True, alpha=0.3)

    def draw_spectrogram(ax, fig, cax=None):
        pcm = ax.pcolormesh(spec_t, spec_f, 10 * np.log10(Sxx + 1e-12),
                            shading="auto", cmap="viridis", rasterized=True)
        for t0 in [5, 10, 15, 20, 25]:
            ax.axvline(t0, color="white", ls="--", alpha=0.6, lw=0.8)
        ax.set_xlim(0, DURATION)
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Frequência (Hz)")
        ax.set_title(f"Espectrograma ({ds.fs} Hz) — bandas verticais escuras = contrações")
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
        ax.set_xlim(0, ds.fs / 2)
        ax.set_xlabel("Frequência (Hz)")
        ax.set_ylabel("Magnitude FFT (linear)")
        ax.set_title(f"Espectro médio: repouso vs contração ({ds.fs} Hz, FFT linear)")
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)

    def draw_welch_psd(ax):
        ax.semilogy(welch_freqs, welch_rest, label="Repouso", color="tab:blue", lw=1.5)
        ax.semilogy(welch_freqs, welch_flex, label="Contração", color="tab:red", lw=1.5)
        ax.axvspan(*EMG_BAND, color="green", alpha=0.07)
        for hz in MAINS_HARMONICS:
            ax.axvline(hz, color="grey", ls=":", alpha=0.6)
        ax.set_xlim(0, ds.fs / 2)
        ax.set_xlabel("Frequência (Hz)")
        ax.set_ylabel("PSD (log)")
        ax.set_title(f"PSD (Welch, log, {ds.fs} Hz) — visão suave dos espectros")
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, which="both", alpha=0.3)

    return draw_timeseries, draw_spectrogram, draw_fft, draw_welch_psd


def analyze(ds: Dataset):
    print(f"\n=== {ds.label} ({ds.csv}, fs={ds.fs} Hz) ===")
    sig, t = load(ds)
    print(f"Loaded {len(sig)} samples ({t[-1]:.2f} s)")

    fft_freqs, fft_rest = avg_fft(sig, t, REST_WINDOWS, ds.fs)
    _,         fft_flex = avg_fft(sig, t, FLEX_WINDOWS, ds.fs)
    welch_freqs, welch_rest = avg_welch(sig, t, REST_WINDOWS, ds.fs)
    _,           welch_flex = avg_welch(sig, t, FLEX_WINDOWS, ds.fs)
    spec_f, spec_t, Sxx = spectrogram(sig - sig.mean(), fs=ds.fs,
                                       nperseg=min(512, len(sig) // 30),
                                       noverlap=min(256, len(sig) // 60))

    draw_ts, draw_sp, draw_fft, draw_wp = make_drawers(
        ds, sig, t, fft_freqs, fft_rest, fft_flex,
        welch_freqs, welch_rest, welch_flex, spec_f, spec_t, Sxx,
    )

    out_dir = os.path.join(SCRIPT_DIR, ds.label)
    os.makedirs(out_dir, exist_ok=True)

    # Combined 4-panel
    fig = plt.figure(figsize=(12, 14))
    gs = fig.add_gridspec(nrows=4, ncols=2, width_ratios=[1.0, 0.025],
                          hspace=0.45, wspace=0.04)
    ax_time = fig.add_subplot(gs[0, 0])
    ax_spec = fig.add_subplot(gs[1, 0])
    cax_spec = fig.add_subplot(gs[1, 1])
    ax_fft = fig.add_subplot(gs[2, 0])
    ax_welch = fig.add_subplot(gs[3, 0])
    draw_ts(ax_time)
    draw_sp(ax_spec, fig, cax=cax_spec)
    draw_fft(ax_fft)
    draw_wp(ax_welch)
    for ext in ("png", "svg"):
        out = os.path.join(out_dir, f"spectral_analysis.{ext}")
        plt.savefig(out, dpi=SAVE_DPI, bbox_inches="tight")
        print(f"saved {out}")
    plt.close(fig)

    # Individual panels
    individuals = [
        ("panel_timeseries.svg",  draw_ts,  False),
        ("panel_spectrogram.svg", draw_sp, True),
        ("panel_fft.svg",         draw_fft, False),
        ("panel_welch_psd.svg",   draw_wp,  False),
    ]
    for fname, fn, needs_fig in individuals:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        if needs_fig:
            fn(ax, fig)
        else:
            fn(ax)
        plt.tight_layout()
        out = os.path.join(out_dir, fname)
        plt.savefig(out, dpi=SAVE_DPI, bbox_inches="tight")
        plt.close(fig)
    print(f"saved 4 individual SVG panels in {out_dir}")

    # Per-dataset band ratios (returned for the final comparison table)
    ratios = {}
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
        ratios[label] = (r, c, c / r if r > 0 else float("nan"))
    return ratios


# ---------- Run ----------
all_ratios = {ds.label: analyze(ds) for ds in DATASETS}


# ---------- Comparison ----------
print()
print("=" * 78)
print("Razão Contração/Repouso por banda — comparação entre as duas gravações")
print("=" * 78)
header = f"{'Banda':>22} | {'500 Hz C/R':>11} | {'1000 Hz C/R':>12}"
print(header)
print("-" * len(header))
labels = list(all_ratios["500hz"].keys())
for label in labels:
    r500 = all_ratios["500hz"][label][2]
    r1000 = all_ratios["1000hz"][label][2]
    print(f"{label:>22} | {r500:>10.2f}x | {r1000:>11.2f}x")

print()
print("Interpretação esperada (em ambos os fs):")
print("  - Aumento broadband em 20–150 Hz → assinatura de EMG real.")
print("  - Picos 60/120/180 Hz proporcionais ao broadband → rede não domina.")
print("  - <5 Hz é a banda com MENOR ratio → artefato de movimento não é o motor.")
print()
print("Comparação 500 Hz vs 1000 Hz:")
print("  - A 1000 Hz expande Nyquist de 250 Hz para 500 Hz — banda alta de")
print("    sEMG (250-500 Hz) finalmente coberta. Confira a banda 150-250 e")
print("    a inspeção visual da PSD em 250+ Hz na figura de 1000 Hz.")
