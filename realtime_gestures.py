# Collect real time data, put it through the filter, put it through the model
# lowkey all chat <3

import requests

import socket
import time
from collections import deque

import numpy as np
import tensorflow as tf
import joblib

from filtering.filter_data import filter_data


# -----------------------------
# Settings
# -----------------------------

UDP_IP = "0.0.0.0"
UDP_PORT = 9000

MODEL_PATH = "CNNGRU-model/gesture_cnn_gru_sliding_128.keras"
SCALER_PATH = "CNNGRU-model/gesture_scaler_sliding_128.pkl"

WINDOW_SIZE = 192
PREDICT_EVERY = 16

CONFIDENCE_THRESHOLD = 0.85
COOLDOWN_SECONDS = 0.7

GESTURE_CODES = [
    "D", "De", "Dn", "Ds", "DUD", "Dw",
    "N", "U", "Ue", "Un", "Uw"
]

NEUTRAL_LABEL = "N"

BACKEND_URL = "http://127.0.0.1:8000/gesture"

# -----------------------------
# Load model and scaler
# -----------------------------

model = tf.keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

buffer = deque(maxlen=WINDOW_SIZE)
sample_counter = 0
last_detection_time = 0


# -----------------------------
# UDP setup
# -----------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for IMU data on UDP port {UDP_PORT}")
print("Waiting for watch data...")


# -----------------------------
# Main loop
# -----------------------------

while True:
    packet, addr = sock.recvfrom(1024)
    line = packet.decode("utf-8").strip()

    try:
        # Expected packet:
        # t_ms,ax,ay,az,gx,gy,gz
        parts = line.split(",")

        if len(parts) != 7:
            continue

        t_ms, ax, ay, az, gx, gy, gz = map(float, parts)

        buffer.append([t_ms, ax, ay, az, gx, gy, gz])
        sample_counter += 1

    except ValueError:
        continue

    if len(buffer) < WINDOW_SIZE:
        continue

    if sample_counter % PREDICT_EVERY != 0:
        continue

    rows = np.array(buffer, dtype=float)

    # Convert t_ms to seconds starting from 0
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
        # Real-time/causal filtering
        filtered = filter_data(
            imu_data,
            fs=None,
            realtime=True
        )

    except Exception as e:
        print("Filtering error:", e)
        continue

    # Keep only ax, ay, az, gx, gy, gz
    window = filtered[:, 1:7]

    # Scale using training scaler
    window_scaled = scaler.transform(window)

    # Model expects shape: (1, WINDOW_SIZE, 6)
    x = np.expand_dims(window_scaled, axis=0)

    probs = model.predict(x, verbose=0)[0]
    gesture_id = int(np.argmax(probs))
    confidence = float(np.max(probs))
    gesture = GESTURE_CODES[gesture_id]

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
    except requests.exceptions.RequestException as e:
        print("Could not send gesture to frontend:", e)

    last_detection_time = now