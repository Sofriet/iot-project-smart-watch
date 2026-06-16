/*
 * Waveshare ESP32-S3-Touch-AMOLED-2.06  —  IMU streaming over Wi-Fi (UDP)
 * Streams QMI8658 accelerometer + gyroscope as CSV lines to your laptop.
 *
 * PlatformIO env (platformio.ini):
 *   platform     = espressif32
 *   board        = esp32-s3-devkitc-1
 *   framework    = arduino
 *   lib_deps     = https://github.com/lewisxhe/SensorLib.git
 *   build_flags  = -DARDUINO_USB_CDC_ON_BOOT=1
 *   monitor_speed= 115200
 *
 * Packet format (one UDP datagram per sample, ASCII):
 *   millis,ax,ay,az,gx,gy,gz\n      (accel in g, gyro in deg/s)
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "SensorQMI8658.hpp"

// ----------------------- USER CONFIG -----------------------
const char *WIFI_SSID = "iPhone van Sofie";
const char *WIFI_PASS = "lololol320";
const uint16_t LAPTOP_PORT = 9000; // must match the Python receiver
// No laptop IP needed — packets are broadcast to the whole subnet, so the
// receiver picks them up regardless of which address the laptop is given.

// I2C pins for the QMI8658 — COPY THESE from your board demo's pin_config.h.
// (These are the common Waveshare AMOLED values; confirm against your board.)
#define IIC_SDA 15
#define IIC_SCL 14
// -----------------------------------------------------------

SensorQMI8658 qmi;
IMUdata acc;
IMUdata gyr;
WiFiUDP udp;
char buf[128];

void setup()
{
    Serial.begin(115200);
    delay(200);

    Wire.begin(IIC_SDA, IIC_SCL);

    if (!qmi.begin(Wire, QMI8658_L_SLAVE_ADDRESS, IIC_SDA, IIC_SCL))
    {
        Serial.println("QMI8658 not found - check I2C pins / address (0x6B).");
        while (1)
            delay(1000);
    }
    Serial.printf("QMI8658 OK, chip id 0x%X\n", qmi.getChipID());

    // Tune ranges / output data rate (ODR) to your needs. Higher ODR = more data.
    qmi.configAccelerometer(SensorQMI8658::ACC_RANGE_4G,
                            SensorQMI8658::ACC_ODR_500Hz,
                            SensorQMI8658::LPF_MODE_0);
    qmi.configGyroscope(SensorQMI8658::GYR_RANGE_512DPS,
                        SensorQMI8658::GYR_ODR_448_4Hz,
                        SensorQMI8658::LPF_MODE_3);
    qmi.enableAccelerometer();
    qmi.enableGyroscope();

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting Wi-Fi");
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(300);
        Serial.print(".");
    }
    Serial.printf("\nConnected. Watch IP: %s  ->  broadcasting to %s:%u\n",
                  WiFi.localIP().toString().c_str(),
                  WiFi.broadcastIP().toString().c_str(), LAPTOP_PORT);
}

void loop()
{
    if (qmi.getDataReady())
    {
        qmi.getAccelerometer(acc.x, acc.y, acc.z);
        qmi.getGyroscope(gyr.x, gyr.y, gyr.z);

        int n = snprintf(buf, sizeof(buf),
                         "%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",
                         (unsigned long)millis(),
                         acc.x, acc.y, acc.z, gyr.x, gyr.y, gyr.z);

        udp.beginPacket(WiFi.broadcastIP(), LAPTOP_PORT);
        udp.write((const uint8_t *)buf, n);
        udp.endPacket();
    }
}