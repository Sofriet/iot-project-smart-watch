import os
import glob
import pandas as pd
import numpy as np

from filtering.filter_data import filter_data

RAW_DIR = "watch/training-data/gesture_data_june24_sofie_rightarm_sitting"
OUT_DIR = "watch/src/sofie_gesture_data_filtered_24"

print("Current working directory:", os.getcwd())
print("RAW_DIR exists:", os.path.exists(RAW_DIR))
print("OUT_DIR exists:", os.path.exists(OUT_DIR))

raw_files = glob.glob(
    os.path.join(RAW_DIR, "**", "*.csv"),
    recursive=True
)
print("CSV files found:", len(raw_files))
print(raw_files[:5])

os.makedirs(OUT_DIR, exist_ok=True)

for raw_path in raw_files:
    df = pd.read_csv(raw_path)

    # Expected raw columns:
    # sample,t_ms,ax,ay,az,gx,gy,gz,tremor
    required = ["sample", "t_ms", "ax", "ay", "az", "gx", "gy", "gz", "tremor"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        print(f"Skipping {raw_path}: missing columns {missing}")
        continue

    # Convert milliseconds to seconds and start at 0
    time_s = (df["t_ms"] - df["t_ms"].iloc[0]) / 1000.0

    data = np.column_stack([
        time_s,
        df["ax"],
        df["ay"],
        df["az"],
        df["gx"],
        df["gy"],
        df["gz"],
    ])

    try:
        filtered = filter_data(data, fs=None, realtime=False)
    except Exception as e:
        print(f"Failed on {raw_path}: {e}")
        continue

    out_df = pd.DataFrame(
        filtered,
        columns=["t_s", "ax", "ay", "az", "gx", "gy", "gz"]
    )

    # Add labels/metadata back
    out_df.insert(0, "sample", df["sample"].values)
    out_df["t_ms"] = df["t_ms"].values
    out_df["tremor"] = df["tremor"].values

    # Reorder columns nicely
    out_df = out_df[
        ["sample", "t_ms", "t_s", "ax", "ay", "az", "gx", "gy", "gz", "tremor"]
    ]

    filename = os.path.basename(raw_path)
    out_path = os.path.join(OUT_DIR, filename)

    out_df.to_csv(out_path, index=False)
    print(f"Saved filtered file: {out_path}")

print("Done filtering all gesture CSVs.")