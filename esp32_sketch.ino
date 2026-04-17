#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Hackverse-SVIT";
const char* password = "Sai@1234";

const char* serverUrl = "http://192.168.31.55:5000/iot/heartrate";

#define PULSE_PIN 36

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  Serial.print("Connecting...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
}

void loop() {
  int value = analogRead(PULSE_PIN);

  int bpm = map(value, 1000, 3000, 60, 120);

  Serial.print("Raw: ");
  Serial.print(value);
  Serial.print(" | BPM: ");
  Serial.println(bpm);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String json = "{\"patient_id\":\"P12345\",\"bpm\":" + String(bpm) + "}";

    int response = http.POST(json);
    Serial.print("Response: ");
    Serial.println(response);

    http.end();
  }

  delay(2000);
}