import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, fftfreq

# Read the CSV file
data = pd.read_csv('emg_data.csv')

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

# Time domain plot (original signal)
ax1.plot(data['Tempo(s)'], data['EMG_Value'], 'b-', linewidth=1, label='EMG Signal')
ax1.set_title('EMG Signal Over Time', fontsize=14, fontweight='bold')
ax1.set_xlabel('Time (seconds)', fontsize=12)
ax1.set_ylabel('EMG Value (mV)', fontsize=12)
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.legend(fontsize=10)
ax1.set_ylim(data['EMG_Value'].min() - 0.1 * data['EMG_Value'].std(), 
             data['EMG_Value'].max() + 0.1 * data['EMG_Value'].std())
ax1.set_facecolor('#f8f8f8')

# Calculate FFT with known sampling rate
SAMPLING_RATE = 5000  # Hz, from main.py timer configuration
n = len(data['EMG_Value'])
yf = fft(data['EMG_Value'])
xf = fftfreq(n, 1/SAMPLING_RATE)

# Plot only positive frequencies up to Nyquist frequency (2500 Hz)
mask = (xf > 0) & (xf <= SAMPLING_RATE/2)
ax2.plot(xf[mask], 2.0/n * np.abs(yf[mask]), 'r-', linewidth=1, label='FFT')
ax2.set_title('Frequency Spectrum', fontsize=14, fontweight='bold')
ax2.set_xlabel('Frequency (Hz)', fontsize=12)
ax2.set_ylabel('Magnitude', fontsize=12)
ax2.grid(True, linestyle='--', alpha=0.7)
ax2.legend(fontsize=10)
ax2.set_facecolor('#f8f8f8')

# Set x-axis limit to show frequencies up to Nyquist frequency
ax2.set_xlim(0, SAMPLING_RATE/2)

# Adjust layout to prevent label clipping
plt.tight_layout()

# Show the plot
plt.show()