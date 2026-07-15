import os
import matplotlib as mpl
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# File to compare
# --------------------------------------------------
filename = "Ue_no_tremor_9.csv"

RAW_DIR = "watch/src/gesture_data"
FILTERED_DIR = "watch/src/gesture_data_filtered"

raw = pd.read_csv(os.path.join(RAW_DIR, filename))
filtered = pd.read_csv(os.path.join(FILTERED_DIR, filename))

# Time axis (seconds)
t = (raw["t_ms"] - raw["t_ms"].iloc[0]) / 1000.0

mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']

plt.figure(figsize=(10, 4))

plt.plot(
    t,
    raw["ax"],
    label="Raw",
    linewidth=1,
    alpha=0.7
)

plt.plot(
    t,
    filtered["ax"],
    label="Filtered",
    linewidth=2
)

# Removed title to match the simulated figure
plt.xlabel("Time (s)", fontsize=13)
plt.ylabel("Acceleration (x-axis)", fontsize=13)

plt.xlim(t.iloc[0], t.iloc[-1])   # removes whitespace at left/right
plt.margins(x=0)                  # no horizontal padding

plt.grid(True)
plt.legend(loc="upper right")     # change to "lower left" if you prefer that style

plt.tight_layout()
plt.show()