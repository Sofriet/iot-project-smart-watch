#!/usr/bin/env python3
"""
Gesture training-data collector for the Waveshare watch IMU Wi-Fi (UDP) stream.

Run this FIRST, then power on the watch. Find your laptop's IP with
`ipconfig` (Windows) or `ifconfig`/`ip addr` (mac/Linux) and put it in
LAPTOP_IP in the .ino sketch. Make sure your firewall allows UDP 9000.

Workflow
--------
1. A menu of gestures is shown, each mapped to a number key.
2. Press a number key to pick the gesture you want to record.
3. Press SPACE once to START the gesture, perform it, press SPACE again to STOP.
   Everything captured between the two taps is written to one CSV, e.g.
   CW_no_tremor_1.csv, CW_no_tremor_2.csv, ...  (auto-incrementing, never
   overwrites existing files).
4. Press another number key any time to switch to a different gesture.

Tremor flag
-----------
Each recording is tagged tremor / no_tremor (default: no_tremor). Press 't' to
toggle. The flag is written as a column in the CSV AND baked into the filename,
and the tremor and no_tremor variants of a gesture are counted separately
(e.g. CW_no_tremor_*.csv and CW_tremor_*.csv keep independent numbering).

Keys
----
  1..9, 0   select gesture
  SPACE     start / stop recording the current gesture
  t         toggle tremor / no_tremor for the next recordings
  m         reprint the menu
  z         undo (delete) the last sample you just saved
  q         quit

Gesture-code convention
------------------------
  flick direction : n e w s
  wrist orientation: U D   (wrist orientation is the negative of watch orientation)
  circles         : CW CCW

Usage
-----
    python collect_gestures.py                 # saves into ./gesture_data
    python collect_gestures.py my_data_folder  # saves into ./my_data_folder
"""
import glob
import os
import socket
import sys
import threading
import time

PORT = 9000  # must match LAPTOP_PORT in the firmware

# (code, human-readable name).  The code is used for the CSV filename.
GESTURES = [
    ("Uw",  "Quadrant Left"),
    ("Ue",  "Quadrant Right"),
    ("Dn",  "Letter Up"),
    ("Ds",  "Letter Down"),
    ("Dw",  "Letter Left"),
    ("De",  "Letter Right"),
    ("DUD", "Select"),
    ("Un",  "Space"),
    ("CCW", "Backspace"),
    ("CW",  "Autofill"),
    ("U",   "Rotate D to U"),
    ("D",   "Rotate U to D"),
    ("N",   "Neutral")
]

# A local per-row index ("sample") is prepended, and the tremor flag appended,
# to each recording.
COLUMNS = ["sample", "t_ms", "ax", "ay", "az", "gx", "gy", "gz", "tremor"]

# Maps the tremor toggle (a bool) to the label used in filenames and the CSV.
TREMOR_LABELS = {False: "no_tremor", True: "tremor"}


# --------------------------------------------------------------------------- #
# UDP receiver thread
# --------------------------------------------------------------------------- #
class UDPReceiver(threading.Thread):
    """Receives IMU samples in the background and buffers them while recording."""

    def __init__(self, port):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.settimeout(0.5)  # so the loop can notice the stop flag
        self._stop = threading.Event()
        self.lock = threading.Lock()
        self.recording = False
        self.buffer = []
        self.total = 0            # total samples ever received (connection check)
        self.last_seen = 0.0

    def run(self):
        while not self._stop.is_set():
            try:
                data, _addr = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            line = data.decode(errors="ignore").strip()
            if not line:
                continue
            parts = line.split(",")
            # Must be all-numeric.  Stream is: t_ms, ax, ay, az, gx, gy, gz
            try:
                [float(x) for x in parts]
            except ValueError:
                continue
            if len(parts) < 7:
                continue
            sample = parts[-7:]  # keep the last 7 fields (t_ms..gz), drop extras
            self.total += 1
            self.last_seen = time.time()
            with self.lock:
                if self.recording:
                    self.buffer.append(sample)

    def start_recording(self):
        with self.lock:
            self.buffer = []
            self.recording = True

    def stop_recording(self):
        with self.lock:
            self.recording = False
            buf = self.buffer
            self.buffer = []
        return buf

    def stop(self):
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Cross-platform single-key reader
# --------------------------------------------------------------------------- #
if os.name == "nt":
    import msvcrt

    class KeyReader:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def get_key(self):
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):  # function / arrow key prefix
                msvcrt.getwch()         # swallow the second byte
                return ""
            return ch
else:
    import termios
    import tty

    class KeyReader:
        def __enter__(self):
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)  # cbreak keeps Ctrl-C working as SIGINT
            return self

        def __exit__(self, *exc):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

        def get_key(self):
            return sys.stdin.read(1)


# --------------------------------------------------------------------------- #
# File helpers
# --------------------------------------------------------------------------- #
def next_index(out_dir, code, label):
    """Next free N for CODE_LABEL_N.csv so reruns never overwrite, counted
    separately per (gesture, tremor-flag) combo."""
    prefix = f"{code}_{label}"
    nums = []
    for path in glob.glob(os.path.join(out_dir, f"{prefix}_*.csv")):
        stem = os.path.basename(path)[len(prefix) + 1:-4]  # between 'PREFIX_' and '.csv'
        if stem.isdigit():
            nums.append(int(stem))
    return (max(nums) + 1) if nums else 1


def count_samples(out_dir, code, label):
    """How many recordings already exist for this (gesture, tremor-flag) combo."""
    return len(glob.glob(os.path.join(out_dir, f"{code}_{label}_*.csv")))


def save_sample(out_dir, code, label, rows):
    idx = next_index(out_dir, code, label)
    path = os.path.join(out_dir, f"{code}_{label}_{idx}.csv")
    with open(path, "w", newline="") as f:
        f.write(",".join(COLUMNS) + "\n")
        for i, r in enumerate(rows):
            f.write(f"{i}," + ",".join(r) + f",{label}\n")
    return path, idx


# --------------------------------------------------------------------------- #
# Menu / status
# --------------------------------------------------------------------------- #
KEYS = [
    "1", "2", "3", "4", "5",
    "6", "7", "8", "9", "0",
    "a", "s", "d"
]

def key_for_index(i):
    return KEYS[i]

def index_for_key(k):
    try:
        return KEYS.index(k)
    except ValueError:
        return None

def print_menu():
    print("\n  Gestures")
    print("  --------")
    for i, (code, name) in enumerate(GESTURES):
        print(f"   {key_for_index(i)}  {code:<4} {name}")
    print("\n  SPACE start/stop   t tremor   m menu   z undo   q quit\n")


def print_status(rx, idx, tremor):
    code, name = GESTURES[idx]
    label = TREMOR_LABELS[tremor]
    n_no = count_samples(rx_out_dir, code, "no_tremor")
    n_tr = count_samples(rx_out_dir, code, "tremor")
    nxt = next_index(rx_out_dir, code, label)
    live = "streaming" if (time.time() - rx.last_seen) < 1.5 else "no data yet"
    state = "ON" if tremor else "OFF"
    print(f"  selected: {code} ({name})   tremor: {state} ({label})")
    print(f"    counts -> no_tremor: {n_no}   tremor: {n_tr}")
    print(f"    next file: {code}_{label}_{nxt}.csv   [watch: {live}]")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
rx_out_dir = "gesture_data"  # module-level so print_status can read it


def main():
    global rx_out_dir
    rx_out_dir = sys.argv[1] if len(sys.argv) > 1 else "gesture_data"
    os.makedirs(rx_out_dir, exist_ok=True)

    rx = UDPReceiver(PORT)
    rx.start()

    print(f"Listening on UDP :{PORT}  -> saving to ./{rx_out_dir}/")
    print("Power on the watch now. Press a number to pick a gesture.")
    print_menu()

    current = 0          # default to first gesture
    tremor = False       # default: no_tremor
    saved_stack = []     # session history of saved files, for undo
    print_status(rx, current, tremor)

    try:
        with KeyReader() as kr:
            while True:
                k = kr.get_key()

                if k == "\x03":  # Ctrl-C (Windows path doesn't raise)
                    break

                # ---- while RECORDING, only SPACE (stop) and q matter ----
                if rx.recording:
                    if k == " ":
                        rows = rx.stop_recording()
                        code, _ = GESTURES[current]
                        label = TREMOR_LABELS[tremor]
                        if not rows:
                            print("  (!) no samples captured — is the watch "
                                  "streaming? nothing saved")
                        else:
                            path, idx = save_sample(rx_out_dir, code, label, rows)
                            saved_stack.append(path)
                            try:
                                dur = (float(rows[-1][0]) - float(rows[0][0])) / 1000.0
                            except (ValueError, IndexError):
                                dur = 0.0
                            print(f"  saved {path}  "
                                  f"({len(rows)} samples, {dur:.2f}s)")
                            print_status(rx, current, tremor)
                    elif k in ("q",):
                        rx.stop_recording()
                        break
                    continue

                # ---- not recording ----
                if k == " ":
                    rx.start_recording()
                    code, name = GESTURES[current]
                    label = TREMOR_LABELS[tremor]
                    print(f"  ● REC  {code} ({name}) [{label}] ... "
                          f"press SPACE to stop")
                elif k in ("q",):
                    break
                elif k in ("t", "T"):
                    tremor = not tremor
                    print_status(rx, current, tremor)
                elif k in ("m", "M"):
                    print_menu()
                    print_status(rx, current, tremor)
                elif k in ("z", "Z"):
                    if saved_stack:
                        last = saved_stack.pop()
                        try:
                            os.remove(last)
                            print(f"  undone: deleted {last}")
                        except OSError as e:
                            print(f"  could not delete {last}: {e}")
                    else:
                        print("  nothing to undo this session")
                    print_status(rx, current, tremor)
                else:
                    idx = index_for_key(k)
                    if idx is not None:
                        current = idx
                        print_status(rx, current, tremor)
    except KeyboardInterrupt:
        pass
    finally:
        rx.stop()
        print(f"\nStopped. Received {rx.total} samples total.")


if __name__ == "__main__":
    main()