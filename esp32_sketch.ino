/*
 * VitaCore — ESP32 Heart Rate Sensor
 * Hardware: ESP32 + MAX30102 pulse oximeter
 *
 * Libraries required (Arduino Library Manager):
 *   - WiFi (built-in ESP32)
 *   - HTTPClient (built-in ESP32)
 *   - ArduinoJson by Benoit Blanchon
 *   - SparkFun MAX3010x Pulse and Proximity Sensor Library
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "MAX30105.h"
#include "heartRate.h"

// ── Configuration ─────────────────────────────────────────────────────────────
const char* WIFI_SSID       = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";
const char* BACKEND_URL     = "http://192.168.1.100:5000/iot/heartrate"; // Your PC IP
const char* PATIENT_ID      = "P12345678";
const int   POST_INTERVAL_MS = 2000;  // Post every 2 seconds

// ── Sensor & BPM state ────────────────────────────────────────────────────────
MAX30105 particleSensor;
const byte RATE_SIZE = 4;
byte   rates[RATE_SIZE];
byte   rateSpot = 0;
long   lastBeat = 0;
float  beatsPerMinute;
int    beatAvg;

void setup() {
  Serial.begin(115200);
  Serial.println("\n🫀 VitaCore ESP32 Sensor Starting...");

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n✅ WiFi connected: " + WiFi.localIP().toString());

  // Init sensor
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("❌ MAX30102 not found — check wiring!");
    while (true);
  }
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);
  Serial.println("✅ Sensor initialized. Place finger on sensor.");
}

unsigned long lastPost = 0;

void loop() {
  long irValue = particleSensor.getIR();

  if (checkForBeat(irValue)) {
    long delta = millis() - lastBeat;
    lastBeat   = millis();
    beatsPerMinute = 60 / (delta / 1000.0);

    if (beatsPerMinute < 255 && beatsPerMinute > 20) {
      rates[rateSpot++] = (byte)beatsPerMinute;
      rateSpot %= RATE_SIZE;
      beatAvg = 0;
      for (byte x = 0; x < RATE_SIZE; x++) beatAvg += rates[x];
      beatAvg /= RATE_SIZE;
    }
  }

  // Post to backend every POST_INTERVAL_MS
  if (millis() - lastPost >= POST_INTERVAL_MS && beatAvg > 0) {
    lastPost = millis();
    postHeartRate(beatAvg);
    Serial.printf("💓 BPM: %d  |  IR: %ld\n", beatAvg, irValue);
  }

  if (irValue < 50000) {
    Serial.println("  ⚠️  No finger detected...");
  }
}

void postHeartRate(int bpm) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc;
  doc["patient_id"]  = PATIENT_ID;
  doc["heart_rate"]  = bpm;
  doc["sensor"]      = "MAX30102_ESP32";

  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  Serial.printf("  POST %s → %d\n", BACKEND_URL, code);
  http.end();
}
