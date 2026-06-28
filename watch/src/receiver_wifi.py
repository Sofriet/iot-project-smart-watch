#!/usr/bin/env python3
"""
Laptop receiver for the Waveshare watch IMU Wi-Fi (UDP) stream.

Run this FIRST, then power on the watch. Find your laptop's IP with
`ipconfig` (Windows) or `ifconfig`/`ip addr` (mac/Linux) and put it in
LAPTOP_IP in the .ino sketch. Make sure your firewall allows UDP 9000.

Usage:
    python receiver_wifi.py            # print to console
    python receiver_wifi.py log.csv    # also append to a CSV file
"""

import socket
import sys
import time

PORT = 9000          # must match LAPTOP_PORT in the firmware
COLUMNS = ["sample","t_ms", "ax", "ay", "az", "gx", "gy", "gz"]


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    csv_file = None
    if csv_path:
        csv_file = open(csv_path, "a", buffering=1)
        if csv_file.tell() == 0:
            csv_file.write(",".join(COLUMNS) + "\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    print(f"Listening on UDP :{PORT}  (Ctrl+C to stop)")

    n, t0 = 0, time.time()
    try:
        while True:
            data, _addr = sock.recvfrom(2048)
            line = data.decode(errors="ignore").strip()
            if not line:
                continue

            # Parse: t_ms, ax, ay, az, gx, gy, gz
            try:
                vals = [float(x) for x in line.split(",")]
            except ValueError:
                continue

            if csv_file:
                csv_file.write(line + "\n")

            n += 1
            if n % 200 == 0:                       # show running rate
                rate = n / (time.time() - t0)
                print(f"[{rate:6.1f} Hz] {line}")
    except KeyboardInterrupt:
        print(f"\nStopped. Received {n} samples.")
    finally:
        if csv_file:
            csv_file.close()


if __name__ == "__main__":
    main()