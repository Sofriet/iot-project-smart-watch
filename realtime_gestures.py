# Collect real time data, put it through the filter, put it through the model
# lowkey all chat <3

import requests

import socket
import time
from collections import deque

import numpy as np
import tensorflow as tf
import joblib

import matplotlib.pyplot as plt
import os

from filtering.filter_data import filter_data 

UDP_IP = "0.0.0.0" 
UDP_PORT = 9000

MODEL_PATH = "CNNGRU-model/gesture_cnn_gru_sliding_128.keras"
SCALER_PATH = "CNNGRU-model/gesture_scaler_sliding_128.pkl"

WINDOW_SIZE = 128
# PREDICT_EVERY = 16

CONFIDENCE_THRESHOLD = 0.80
# COOLDOWN_SECONDS = 0.7

#chat motion###
START_THRESHOLD = 1.8      # Motion energy to start a gesture
END_THRESHOLD = 0.6        # Motion energy considered "still"

MIN_GESTURE_SAMPLES = 40   # Ignore tiny accidental movements
END_COUNT = 12             # Number of consecutive "still" samples

COOLDOWN_SECONDS = 0.35
####

GESTURE_CODES = [
    "D", "De", "Dn", "Ds", "DUD", "Dw",
    "N", "U", "Ue", "Un", "Uw"
]

NEUTRAL_LABEL = "N"

# This should send it to the backend
BACKEND_URL = "http://127.0.0.1:8000/gesture"

SAVE_SEGMENTS = False
SEGMENT_DIR = "realtime_segments"

os.makedirs(SEGMENT_DIR, exist_ok=True)

segment_counter = 0

def save_segment_plot(raw, filtered, prediction, confidence, segment_id):

    time_s = raw[:,0]

    fig, axes = plt.subplots(
        6, 1,
        figsize=(10, 12),
        sharex=True
    )

    labels = [
        "Accelerometer X",
        "Accelerometer Y",
        "Accelerometer Z",
        "Gyroscope X",
        "Gyroscope Y",
        "Gyroscope Z"
    ]

    for i in range(6):

        axes[i].plot(
            time_s,
            raw[:, i+1],
            label="Raw",
            alpha=0.6
        )

        axes[i].plot(
            time_s,
            filtered[:, i+1],
            label="Filtered"
        )

        axes[i].set_ylabel(labels[i])

        if i == 0:
            axes[i].legend()

    axes[-1].set_xlabel("Time (s)")

    fig.suptitle(
        f"Realtime Segment {segment_id}: {prediction} "
        f"({confidence:.2f})"
    )

    plt.tight_layout()

    filename = (
        f"{SEGMENT_DIR}/f0segment_{segment_id}_"
        f"{prediction}_{confidence:.2f}.png"
    )

    plt.savefig(filename, dpi=300)
    plt.close()

    print(f"Saved segment plot: {filename}")
   

model = tf.keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

buffer = deque(maxlen=WINDOW_SIZE)

# sample_counter = 0
# last_detection_time = 0

last_detection_time = 0

# Segmentation state
state = "IDLE"

active_samples = 0
still_counter = 0

prev_acc_mag = None


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for IMU data on UDP port {UDP_PORT}")
print("Waiting for watch data...")

def motion_energy(ax, ay, az, gx, gy, gz, prev_acc_mag):

    acc_mag = np.sqrt(ax**2 + ay**2 + az**2)
    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)

    if prev_acc_mag is None:
        delta_acc = 0
    else:
        delta_acc = abs(acc_mag - prev_acc_mag)

    energy = delta_acc + 0.02 * gyro_mag

    return energy, acc_mag


while True:
    packet, addr = sock.recvfrom(1024)
    print(f"Received packet from {addr}: {packet.decode('utf-8').strip()}")
    line = packet.decode("utf-8").strip()

    try:

        parts = line.split(",")

        kn, t_ms, ax, ay, az, gx, gy, gz = map(float, parts)

        buffer.append([t_ms, ax, ay, az, gx, gy, gz])
        print(f"Buffer size: {len(buffer)}")

        energy, prev_acc_mag = motion_energy(
            ax,
            ay,
            az,
            gx,
            gy,
            gz,
            prev_acc_mag
        )

    except ValueError:
        continue

    if len(buffer) < WINDOW_SIZE:
        continue

    if state == "IDLE":

        if energy > START_THRESHOLD:

            state = "COLLECTING"

            active_samples = 0
            still_counter = 0

            print("Motion started")

    elif state == "COLLECTING":

        active_samples += 1

        if energy < END_THRESHOLD:

            still_counter += 1

        else:

            still_counter = 0

        if (
            still_counter >= END_COUNT
            and
            active_samples >= MIN_GESTURE_SAMPLES
        ):

            state = "PREDICT"

    elif state == "COOLDOWN":

        if time.time() - last_detection_time > COOLDOWN_SECONDS:

            state = "IDLE"

    if state != "PREDICT":
        continue


    
    rows = np.array(buffer, dtype=float)

    time_s = (rows[:, 0] - rows[0, 0]) / 1000.0

    imu_data = np.column_stack([
        time_s,
        rows[:, 1],  # ax
        rows[:, 2],  # ay
        rows[:, 3],  # az
        rows[:, 4],  # gx
        rows[:, 5],  # gy
        rows[:, 6],  # gz
    ])

    try:

        filtered = filter_data(
            imu_data,
            fs=None,
            realtime=False
        )

    except Exception as e:
        print("Filtering error:", e)
        continue

    print(f"Filtered data")
    # Keep only ax, ay, az, gx, gy, gz
    raw_window = imu_data.copy()

    window = filtered[:, 1:7]

    # Scale using training scaler
    window_scaled = scaler.transform(window)

    # Model expects shape: (1, WINDOW_SIZE, 6)
    x = np.expand_dims(window_scaled, axis=0)

    probs = model.predict(x, verbose=0)[0]
    gesture_id = int(np.argmax(probs))
    confidence = float(np.max(probs))
    gesture = GESTURE_CODES[gesture_id]

    if SAVE_SEGMENTS:

        save_segment_plot(
            raw_window,
            filtered,
            gesture,
            confidence,
            segment_counter
        )

    segment_counter += 1

    now = time.time()

    # Ignore Neutral
    if gesture == NEUTRAL_LABEL:
        continue

    # Only output confident predictions
    if confidence < CONFIDENCE_THRESHOLD:
        continue

    # Cooldown prevents the same gesture from printing repeatedly
    if now - last_detection_time < COOLDOWN_SECONDS:
        continue


    if gesture != "N" and confidence >= CONFIDENCE_THRESHOLD:
        print(f"Detected gesture: {gesture} confidence={confidence:.2f}")

    try:
        requests.post(
            BACKEND_URL,
            json={"gesture": gesture},
            timeout=0.2
        )
        print(f"Sent gesture '{gesture}' to backend")

    except requests.exceptions.RequestException as e:
        print("Could not send gesture to frontend:", e)

    last_detection_time = now

    state = "COOLDOWN"

    active_samples = 0
    still_counter = 0