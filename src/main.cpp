/*
 * Waveshare ESP32-S3-Touch-AMOLED-2.06
 * Combined: AMOLED display + QMI8658 IMU + Wi-Fi UDP broadcast streaming
 *           + on-screen Wi-Fi setup portal (no hardcoded credentials).
 *
 * Pins are from Waveshare's Mylibrary/pin_config.h for THIS board.
 *
 * LIBRARIES (PlatformIO lib/ folder or lib_deps):
 *   - GFX_Library_for_Arduino  <-- USE WAVESHARE'S DEMO COPY (has Arduino_CO5300
 *                                  + Display_Brightness). Copy it into lib/.
 *   - SensorLib                (https://github.com/lewisxhe/SensorLib.git)
 *   - WiFiManager              (https://github.com/tzapu/WiFiManager.git)
 *
 * platformio.ini build_flags: -DARDUINO_USB_CDC_ON_BOOT=1
 *
 * The screen shows live status + IMU values; streaming runs at full rate.
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WiFiManager.h>
#include <Arduino_GFX_Library.h>
#include "SensorQMI8658.hpp"

// ---------- Pins (Waveshare Mylibrary/pin_config.h) ----------
#define LCD_SDIO0 4
#define LCD_SDIO1 5
#define LCD_SDIO2 6
#define LCD_SDIO3 7
#define LCD_SCLK 11
#define LCD_CS 12
#define LCD_RESET 8
#define LCD_WIDTH 410
#define LCD_HEIGHT 502
#define IIC_SDA 15
#define IIC_SCL 14
#define BOOT_BTN 0 // BOOT = GPIO0, active LOW
const uint16_t LAPTOP_PORT = 9000;
// -------------------------------------------------------------

// Display objects (CO5300 over QSPI)
Arduino_DataBus *bus = new Arduino_ESP32QSPI(
    LCD_CS, LCD_SCLK, LCD_SDIO0, LCD_SDIO1, LCD_SDIO2, LCD_SDIO3);
Arduino_CO5300 *gfx = new Arduino_CO5300(
    bus, LCD_RESET, 0 /*rotation 0-3*/, LCD_WIDTH, LCD_HEIGHT,
    23 /*col_offset1 - TUNE THIS*/, 0, 0, 0);

SensorQMI8658 qmi;
IMUdata acc, gyr;
WiFiUDP udp;
char buf[128];
uint32_t lastScreen = 0;

// Draw one labelled value line, clearing its row first (avoids flicker buildup).
void field(int y, const char *label, const String &value, uint16_t valColor)
{
    gfx->fillRect(0, y, LCD_WIDTH, 26, BLACK);
    gfx->setTextSize(2);
    gfx->setCursor(12, y);
    gfx->setTextColor(WHITE);
    gfx->print(label);
    gfx->setTextColor(valColor);
    gfx->print(value);
}

// Called by WiFiManager when it starts the setup access point.
void onPortal(WiFiManager *)
{
    gfx->fillScreen(BLACK);
    gfx->setTextSize(3);
    gfx->setTextColor(CYAN);
    gfx->setCursor(12, 30);
    gfx->println("Wi-Fi setup");
    gfx->setTextSize(2);
    gfx->setTextColor(WHITE);
    gfx->setCursor(12, 110);
    gfx->println("1) Join Wi-Fi:");
    gfx->setTextColor(YELLOW);
    gfx->setCursor(12, 140);
    gfx->println("   WatchIMU-Setup");
    gfx->setTextColor(WHITE);
    gfx->setCursor(12, 170);
    gfx->println("   pw: watch1234");
    gfx->setCursor(12, 220);
    gfx->println("2) Open in browser:");
    gfx->setTextColor(YELLOW);
    gfx->setCursor(12, 250);
    gfx->println("   192.168.4.1");
    gfx->setTextColor(WHITE);
    gfx->setCursor(12, 300);
    gfx->println("3) Pick network, save");
}

void setup()
{
    Serial.begin(115200);
    pinMode(BOOT_BTN, INPUT_PULLUP);

    // ---- Display ----
    gfx->begin();
    gfx->setBrightness(255); // Waveshare GFX method; if it won't compile,
                             // your GFX library isn't Waveshare's build.
    gfx->fillScreen(BLACK);
    gfx->setTextSize(3);
    gfx->setTextColor(WHITE);
    gfx->setCursor(12, 40);
    gfx->println("Starting...");

    // ---- IMU ----
    Wire.begin(IIC_SDA, IIC_SCL);
    if (!qmi.begin(Wire, QMI8658_L_SLAVE_ADDRESS, IIC_SDA, IIC_SCL))
    {
        gfx->setTextColor(RED);
        gfx->setCursor(12, 100);
        gfx->println("IMU not found");
        while (1)
            delay(1000);
    }
    qmi.configAccelerometer(SensorQMI8658::ACC_RANGE_4G,
                            SensorQMI8658::ACC_ODR_500Hz,
                            SensorQMI8658::LPF_MODE_0);
    qmi.configGyroscope(SensorQMI8658::GYR_RANGE_512DPS,
                        SensorQMI8658::GYR_ODR_448_4Hz,
                        SensorQMI8658::LPF_MODE_3);
    qmi.enableAccelerometer();
    qmi.enableGyroscope();

    // ---- Wi-Fi (portal-based, shows instructions on screen) ----
    WiFiManager wm;
    if (digitalRead(BOOT_BTN) == LOW)
        wm.resetSettings(); // hold BOOT = reconfigure
    wm.setAPCallback(onPortal);
    wm.setConfigPortalTimeout(180);
    if (!wm.autoConnect("WatchIMU-Setup", "watch1234"))
    {
        ESP.restart();
    }

    // ---- Static status layout ----
    gfx->fillScreen(BLACK);
    gfx->setTextSize(3);
    gfx->setTextColor(GREEN);
    gfx->setCursor(12, 20);
    gfx->println("Streaming");
    field(80, "IP:  ", WiFi.localIP().toString(), CYAN);
    field(112, "->   ", WiFi.broadcastIP().toString() + ":" + String(LAPTOP_PORT), CYAN);
}

void loop()
{
    // Stream every available sample at full rate.
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

    // Refresh the screen only ~8x/sec so drawing doesn't slow the stream.
    if (millis() - lastScreen > 120)
    {
        lastScreen = millis();
        char a[40], g[40];
        snprintf(a, sizeof(a), "%.2f %.2f %.2f   ", acc.x, acc.y, acc.z);
        snprintf(g, sizeof(g), "%.1f %.1f %.1f   ", gyr.x, gyr.y, gyr.z);
        field(180, "acc: ", a, YELLOW);
        field(212, "gyr: ", g, YELLOW);
    }
}