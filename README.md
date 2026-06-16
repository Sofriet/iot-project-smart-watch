# watch-imu

A small Wi-Fi streaming project for the Waveshare ESP32-S3 touch AMOLED watch.

The watch firmware reads the QMI8658 IMU and sends accelerometer and gyroscope measurements over UDP to a laptop. A Python receiver script listens on UDP port 9000, prints the live stream, and can also save the data to CSV.

## Project structure

- `platformio.ini` - PlatformIO configuration for the ESP32-S3 Arduino firmware.
- `src/main.cpp` - ESP32 firmware that reads IMU data and sends UDP packets to the laptop.
- `src/receiver_wifi.py` - Laptop-side Python receiver for UDP IMU data.
- `include/` - Header files and project-specific includes.
- `lib/` - Libraries required by the firmware.

## Hardware

- Waveshare ESP32-S3-Touch-AMOLED-2.06 board (or compatible ESP32-S3 board)
- QMI8658 IMU sensor
- Wi-Fi network available for the watch and laptop

## How it works

1. The ESP32 connects to a Wi-Fi network.
2. It reads accelerometer and gyroscope values from the QMI8658 IMU.
3. Each sample is sent as a single UDP packet to the laptop.
4. The laptop runs `receiver_wifi.py` to receive, display, and optionally log the data.

## Firmware configuration

Open `src/main.cpp` and update the Wi-Fi and laptop settings:

```cpp
const char *WIFI_SSID = "iPhone van Sofie";
const char *WIFI_PASS = "lololol320";
const char *LAPTOP_IP = "172.20.10.2"; // your laptop IP on the same network
const uint16_t LAPTOP_PORT = 9000;
```

Also confirm the I2C pins match your board:

```cpp
#define IIC_SDA 15
#define IIC_SCL 14
```

## Data format

The watch sends one UDP packet per sample in CSV format:

```
millis,ax,ay,az,gx,gy,gz
```

- `millis` - timestamp in milliseconds since boot
- `ax`, `ay`, `az` - accelerometer values in g
- `gx`, `gy`, `gz` - gyroscope values in degrees per second

## Running the laptop receiver

1. Make sure your firewall allows UDP traffic on port `9000`.
2. Run the receiver:

```bash
python3 src/receiver_wifi.py
```

3. To also log data to CSV:

```bash
python3 src/receiver_wifi.py log.csv
```

The script prints live messages and writes `log.csv` if a filename is provided.

## Building and uploading firmware

Use PlatformIO from the project root:

```bash
pio run --target upload
```

Then open the serial monitor if you want to watch the boot logs:

```bash
pio device monitor
```

## Notes

- Power the watch and connect it to the same Wi-Fi network as your laptop.
- Start `receiver_wifi.py` before powering on the watch to capture all UDP packets.
- If packets are missing or the connection fails, verify the `LAPTOP_IP` and port in the firmware match your laptop settings.

## License

This project is provided as-is for personal use and experimentation.
