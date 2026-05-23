"""EMG filter + FFT analysis.

Loads a 500 Hz EMG recording, applies a 60 Hz notch filter and a
20-240 Hz band-pass, and plots:
  - time-domain signal (raw vs filtered),
  - FFT magnitude of the filtered signal,
  - FFT magnitude of the raw signal (zoomed Y axis).

Converted from the original notebook ``cods_protese_emg.ipynb`` and
cleaned up; see ``README.md`` in this directory for the change log.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt

# ======================
# CONFIGURAÇÕES
# ======================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "..", "rec_emg", "new_emg_data8.csv")

fs = 500            # taxa de amostragem (Hz)
lowcut = 20         # passa-faixa: corte inferior (Hz)
highcut = 240       # passa-faixa: corte superior (Hz)
notch_freq = 60     # notch: rede elétrica (Hz)
notch_Q = 30        # notch: fator de qualidade (quanto maior, mais estreito)

# ======================
# CARREGAR DADOS
# ======================
df = pd.read_csv(CSV_PATH)
signal = df["EMG_Value"].values

# ======================
# 1. FILTRO NOTCH 60 Hz
# ======================
b_notch, a_notch = iirnotch(notch_freq, notch_Q, fs)
signal_notch = filtfilt(b_notch, a_notch, signal)

# ======================
# 2. FILTRO PASSA-FAIXA 20-240 Hz
# ======================
sos = butter(4, [lowcut, highcut], btype="bandpass", fs=fs, output="sos")
signal_filtered = sosfiltfilt(sos, signal_notch)

print("Filtragem concluída!")

# =========================
# PLOT 1 — TEMPO (matplotlib)
# =========================
t = np.arange(len(signal)) / fs

plt.figure(figsize=(12, 6))
plt.plot(t, signal, label="Sinal Original", alpha=0.6)
plt.plot(t, signal_filtered, label="Sinal Filtrado", linewidth=2)
plt.xlabel("Tempo (s)")
plt.ylabel("Amplitude do Sinal (ADC)")
plt.title(f"Sinal EMG ({fs} Hz) — Original vs Filtrado")
plt.legend()
plt.grid()
plt.show()


def plot_fft(x, fs, title, y_range=None):
    """Plot one-sided FFT magnitude of x using Plotly.

    Magnitude is divided by 1e6 only for display readability — y-axis label
    reflects that with the 'x 10^-6' suffix.
    """
    n = len(x)
    yf = np.fft.fft(x)
    xf = np.fft.fftfreq(n, 1 / fs)
    pos = xf > 0
    freqs = xf[pos]
    mag = np.abs(yf[pos]) * 2 / 1e6  # *2: one-sided scaling; /1e6: display only

    fig = go.Figure(data=[go.Scatter(x=freqs, y=mag, mode="lines", name="Magnitude")])
    fig.update_layout(
        title=title,
        xaxis_title="Frequência (Hz)",
        yaxis_title="Magnitude (× 10⁻⁶)",
        xaxis_range=[0, fs / 2],  # até Nyquist
    )
    if y_range is not None:
        fig.update_layout(yaxis_range=y_range)
    fig.show()


# =========================
# PLOT 2 — FFT DO SINAL FILTRADO
# =========================
plot_fft(signal_filtered, fs, "Espectro do Sinal EMG Filtrado (FFT)")

# =========================
# PLOT 3 — FFT DO SINAL BRUTO (zoom em Y)
# =========================
plot_fft(signal, fs, "Espectro do Sinal EMG Bruto (FFT)", y_range=[0, 4])
