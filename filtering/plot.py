import os
import matplotlib as mpl
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# File to compare
# --------------------------------------------------
filename = "Dw_tremor_24.csv"

RAW_DIR = "watch/src/gesture_data"
FILTERED_DIR = "watch/src/gesture_data_filtered"

raw = pd.read_csv(os.path.join(RAW_DIR, filename))
filtered = pd.read_csv(os.path.join(FILTERED_DIR, filename))

# Time axis (seconds)
t = (raw["t_ms"] - raw["t_ms"].iloc[0]) / 1000.0

channels = [
    ("ax", "Accelerometer X"),
    ("ay", "Accelerometer Y"),
    ("az", "Accelerometer Z"),
    ("gx", "Gyroscope X"),
    ("gy", "Gyroscope Y"),
    ("gz", "Gyroscope Z"),
]

mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']  

fig, axes = plt.subplots(6, 1, figsize=(12, 14), sharex=True)

for ax, (col, title) in zip(axes, channels):

    ax.plot(
        t,
        raw[col],
        label="Raw",
        linewidth=1,
        alpha=0.7
    )

    ax.plot(
        t,
        filtered[col],
        label="Filtered",
        linewidth=2
    )

    ax.set_ylabel(col)
    ax.set_title(title)
    ax.grid(True)

axes[0].legend()

axes[-1].set_xlabel("Time (s)")

plt.suptitle("   ")

plt.tight_layout()

plt.show()