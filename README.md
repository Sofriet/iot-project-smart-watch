# watch-imu

A small Wi-Fi streaming project for the Waveshare ESP32-S3 touch AMOLED watch.

The watch firmware reads the QMI8658 IMU, shows status on the display, and sends accelerometer and gyroscope measurements over UDP to a laptop. A built-in Wi-Fi setup portal lets you configure network credentials without hardcoded values.

A Python receiver script listens on UDP port 9000, prints the live stream, and can also save the data to CSV.

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

The current firmware uses a Wi-Fi setup portal instead of hardcoded SSID and password values.

If you hold the boot button while powering on the watch, it will reset saved Wi-Fi settings and start the portal access point `WatchIMU-Setup` with password `watch1234`.

Then open `http://192.168.4.1` in a browser to select your network and save credentials.

Also confirm the I2C pins match your board:

```cpp
#define IIC_SDA 15
#define IIC_SCL 14
```

The watch broadcasts UDP packets to the entire subnet, so no specific laptop IP is required.

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

Use PlatformIO from the project root. First, find your USB port (e.g., `/dev/ttyACM0` on Linux/Mac or `COM3` on Windows), then:

```bash
~/.platformio/penv/bin/pio run -t upload --upload-port /dev/ttyACM0
```

Then open the serial monitor if you want to watch the boot logs:

```bash
pio device monitor
```

## Notes

- Power the watch and connect it to the same Wi-Fi network as your laptop.
- Start `receiver_wifi.py` before powering on the watch to capture all UDP packets.
- The watch broadcasts to the subnet, so any device listening on UDP port 9000 will receive the packets.
- If packets are missing or the connection fails, verify both devices are on the same Wi-Fi network and your firewall allows UDP traffic.

## TODO

- Add touch-screen configuration so Wi-Fi can be set directly from the display instead of the browser portal.

## License

This project is provided as-is for personal use and experimentation.
