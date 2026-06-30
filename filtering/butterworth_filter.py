import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt, sosfiltfilt, welch

def butterworth_filter(signal, fs, cutoff=3.0, order=4, realtime=True):
    sos = butter(N=order, Wn=cutoff, btype='low', fs=fs, output='sos')
 
    if realtime:
        return sosfilt(sos, signal)
    else:
        return sosfiltfilt(sos, signal)