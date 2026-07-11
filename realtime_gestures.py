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

UDP_IP = "0.0.0.0" 
UDP_PORT = 9000

MODEL_PATH = "CNNGRU-model/gesture_cnn_gru_sliding_128.keras"
SCALER_PATH = "CNNGRU-model/gesture_scaler_sliding_128.pkl"

WINDOW_SIZE = 128
# PREDICT_EVERY = 16

CONFIDENCE_THRESHOLD = 0.85
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

# -----------------------------
# Load model and scaler
# -----------------------------

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


# -----------------------------
# UDP setup
# -----------------------------

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

# -----------------------------
# Main loop
# -----------------------------

while True:
    packet, addr = sock.recvfrom(1024)
    print(f"Received packet from {addr}: {packet.decode('utf-8').strip()}")
    line = packet.decode("utf-8").strip()

    try:
        # Expected packet:
        # t_ms,ax,ay,az,gx,gy,gz
        parts = line.split(",")

        # if len(parts) != 8:
        #     continue

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
        # sample_counter += 1

    except ValueError:
        continue

    if len(buffer) < WINDOW_SIZE:
        continue

        ###################################################
    # Motion segmentation state machine
    ###################################################

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

        # Gesture has ended
        if (
            still_counter >= END_COUNT
            and
            active_samples >= MIN_GESTURE_SAMPLES
        ):

            state = "PREDICT"

    elif state == "COOLDOWN":

        if time.time() - last_detection_time > COOLDOWN_SECONDS:

            state = "IDLE"


        # if sample_counter % PREDICT_EVERY != 0:
        #     continue

    if state != "PREDICT":
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

    print(f"Filtered data")
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
        print(f"Sent gesture '{gesture}' to backend")

    except requests.exceptions.RequestException as e:
        print("Could not send gesture to frontend:", e)

    last_detection_time = now

    state = "COOLDOWN"

    active_samples = 0
    still_counter = 0