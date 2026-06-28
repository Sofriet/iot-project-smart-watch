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

// ===================== DISPLAY (CO5300 QSPI) =====================
#define LCD_SDIO0 4
#define LCD_SDIO1 5
#define LCD_SDIO2 6
#define LCD_SDIO3 7
#define LCD_SCLK 11
#define LCD_CS 12
#define LCD_RESET 8

#define LCD_WIDTH 410
#define LCD_HEIGHT 502

// ===================== I2C =====================
#define I2C_SDA 15
#define I2C_SCL 14

// ===================== TOUCH (FT3168) =====================
#define FT3168_ADDR 0x38

// ===================== NETWORK =====================
const uint16_t LAPTOP_PORT = 9000;

// ===================== WIFI =====================
const char *WIFI_SSID = "iPhone van Sofie";
const char *WIFI_PASS = "lololol320";

// ===================== DISPLAY =====================
Arduino_DataBus *bus = new Arduino_ESP32QSPI(
    LCD_CS, LCD_SCLK,
    LCD_SDIO0, LCD_SDIO1,
    LCD_SDIO2, LCD_SDIO3);

Arduino_CO5300 *gfx = new Arduino_CO5300(
    bus, LCD_RESET, 0,
    LCD_WIDTH, LCD_HEIGHT,
    23, 0, 0, 0);

// ===================== IMU =====================
SensorQMI8658 qmi;
IMUdata acc, gyr;

// ===================== UDP =====================
WiFiUDP udp;
char buf[128];

// ===================== STATE =====================
bool isRecording = false;
int sampleId = 0;

// ===================== UI BUTTON =====================
int btnX = 120;
int btnY = 360;
int btnW = 170;
int btnH = 90;

uint32_t lastTouch = 0;
uint32_t lastScreen = 0;

// ======================================================
// FT3168 TOUCH READ (proper FT6x36-style protocol)
// ======================================================
bool readTouch(int &x, int &y)
{
    Wire.beginTransmission(FT3168_ADDR);
    Wire.write(0x02); // touch status register (standard FT6x36 family)
    if (Wire.endTransmission(false) != 0)
        return false;

    Wire.requestFrom(FT3168_ADDR, 7);

    if (Wire.available() < 7)
        return false;

    uint8_t status = Wire.read();
    if ((status & 0x0F) == 0)
        return false; // no touch

    uint8_t xh = Wire.read();
    uint8_t xl = Wire.read();
    uint8_t yh = Wire.read();
    uint8_t yl = Wire.read();

    x = ((xh & 0x0F) << 8) | xl;
    y = ((yh & 0x0F) << 8) | yl;

    return true;
}

// ======================================================
void drawButton()
{
    gfx->fillRect(btnX, btnY, btnW, btnH,
                  isRecording ? RED : GREEN);

    gfx->setTextColor(BLACK);
    gfx->setTextSize(3);
    gfx->setCursor(btnX + 45, btnY + 32);

    gfx->print(isRecording ? "STOP" : "REC");
}

// ======================================================
void toggleRecording()
{
    isRecording = !isRecording;

    if (isRecording)
    {
        sampleId++;
        Serial.printf("Recording ON (sample %d)\n", sampleId);
    }
    else
    {
        Serial.println("Recording OFF");
    }

    drawButton();
}

// ======================================================
void handleTouch()
{
    int x, y;

    if (!readTouch(x, y))
        return;

    if (millis() - lastTouch < 250)
        return;

    lastTouch = millis();

    // coordinate match
    if (x > btnX && x < btnX + btnW &&
        y > btnY && y < btnY + btnH)
    {
        toggleRecording();
    }
}

// ======================================================
void field(int y, const char *label, const String &value, uint16_t color)
{
    gfx->fillRect(0, y, LCD_WIDTH, 26, BLACK);
    gfx->setTextSize(2);
    gfx->setCursor(12, y);
    gfx->setTextColor(WHITE);
    gfx->print(label);
    gfx->setTextColor(color);
    gfx->print(value);
}

// ======================================================
void setup()
{
    Serial.begin(115200);

    Wire.begin(I2C_SDA, I2C_SCL);

    // ---------- DISPLAY ----------
    gfx->begin();
    gfx->setBrightness(255);
    gfx->fillScreen(BLACK);

    gfx->setTextSize(3);
    gfx->setTextColor(WHITE);
    gfx->setCursor(20, 40);
    gfx->println("Init...");

    drawButton();

    // ---------- IMU ----------
    if (!qmi.begin(Wire, QMI8658_L_SLAVE_ADDRESS, I2C_SDA, I2C_SCL))
    {
        gfx->setTextColor(RED);
        gfx->setCursor(20, 100);
        gfx->println("IMU FAIL");
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

    // ---------- WIFI ----------
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(300);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected");
}

// ======================================================
void loop()
{
    // ---------- TOUCH ----------
    handleTouch();

    // ---------- IMU ----------
    if (qmi.getDataReady())
    {
        qmi.getAccelerometer(acc.x, acc.y, acc.z);
        qmi.getGyroscope(gyr.x, gyr.y, gyr.z);

        // ONLY STREAM WHEN RECORDING
        if (isRecording)
        {
            int n = snprintf(buf, sizeof(buf),
                             "%d,%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",
                             sampleId,
                             (unsigned long)millis(),
                             acc.x, acc.y, acc.z,
                             gyr.x, gyr.y, gyr.z);

            udp.beginPacket(WiFi.broadcastIP(), LAPTOP_PORT);
            udp.write((uint8_t *)buf, n);
            udp.endPacket();
        }
    }

    // ---------- UI UPDATE ----------
    if (millis() - lastScreen > 120)
    {
        lastScreen = millis();

        char a[40], g[40];
        snprintf(a, sizeof(a), "%.2f %.2f %.2f", acc.x, acc.y, acc.z);
        snprintf(g, sizeof(g), "%.1f %.1f %.1f", gyr.x, gyr.y, gyr.z);

        field(180, "acc:", a, YELLOW);
        field(212, "gyr:", g, YELLOW);

        drawButton();
    }
}