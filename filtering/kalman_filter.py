import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt, sosfiltfilt, welch

# Three parts of the code: first we need to generate the synthetic 6-axis data, then a Kalman filter for the accelerometer measurement, and a Butterworth filter for the gyroscope data

# Sampling frequency of the watch
fs = 1000 # Hz
# update this when we know the exact value from the watch!

# Tremor subtracting Kalman filter for a single axis
def kalman_filter(signal, fs, f_tremor=5.0, q_gesture=1e-2, q_tremor=1e-4, r=0.05):
    
    # remor frequency (f_tremor) = 5.0 because it is about the midpoint of literature value for tremors (3-7Hz)
    # q_gesture = gesture model uncertainty
    # q_tremor = tremor stability assumption
    # r = sensor measurement noise

    # Sampling interval = 1 / Sampling frequency
    dt = 1.0 / fs

    # Angular frequency of tremors
    w  = 2 * np.pi * f_tremor

    # Length of signal
    n  = len(signal)
    t  = np.arange(n) * dt
    F = np.array([
        [1, dt,  0,    0  ],
        [0,  1,  0,    0  ],
        [0,  0,  cw,  -sw ],
        [0,  0,  sw,   cw ],
    ])
    Q = np.diag([q_gesture, q_gesture, q_tremor, q_tremor])
    R = np.array([[r]])
 
    x = np.array([signal[0], 0.0, 0.0, 0.0])
    P = np.eye(4) * 0.5

    gesture_est = np.zeros(n) # filtered gesture signaldt
    cw, sw = np.cos(w * dt), np.sin(w * dt)
 
    # State transition: constant-velocity gesture + rotating tremor phasor
    tremor_est  = np.zeros(n) # estimated tremor component
 
    for k in range(n):
        H   = np.array([[1, 0, np.cos(w*t[k]), np.sin(w*t[k])]])
        x_p = F @ x
        P_p = F @ P @ F.T + Q
        S   = H @ P_p @ H.T + R
        K   = P_p @ H.T @ np.linalg.inv(S)
        x   = x_p + K @ (np.array([signal[k]]) - H @ x_p)
        P   = (np.eye(4) - K @ H) @ P_p
        gesture_est[k] = x[0]
        tremor_est[k]  = x[2]*np.cos(w*t[k]) + x[3]*np.sin(w*t[k])
 
    return gesture_est, tremor_est    

