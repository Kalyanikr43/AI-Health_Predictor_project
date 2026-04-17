<<<<<<< HEAD
# 🏥 Health-Twin — AI Health Monitoring System

A full-stack health monitoring application with AI risk analysis, live heart rate tracking, multi-language support, and doctor management.

---

## 📁 Project Structure

```
health_system/
├── frontend/
│   ├── index.html        ← Full single-page app (open in browser)
│   └── i18n.json         ← Translation strings (EN / Telugu / Kannada)
├── backend/
│   ├── app.py            ← Flask REST API
│   └── requirements.txt  ← Python dependencies
└── sensor/
    ├── sensor_mock.py    ← Python mock sensor (simulates ESP32)
    └── esp32_sketch.ino  ← Real ESP32 Arduino sketch
```

---

## 🚀 Quick Start

### 1. Backend (Flask)

```bash
cd backend
pip install -r requirements.txt
python app.py
# → Running at http://localhost:5000
```

### 2. Frontend

Open `frontend/index.html` directly in your browser.

> The frontend works **offline** (demo mode) even without the backend running — all analysis runs locally via JS.

### 3. Mock Sensor (simulates ESP32)

```bash
cd sensor
pip install requests
python sensor_mock.py --patient YOUR_PATIENT_ID --url http://localhost:5000
```

---

## 🔌 Real ESP32 Setup

1. Open `sensor/esp32_sketch.ino` in Arduino IDE
2. Install libraries: `MAX30105`, `ArduinoJson`
3. Fill in your WiFi credentials and backend URL
4. Flash to ESP32 (tested with ESP32-WROOM-32)
5. The ESP32 will POST to `/iot/heartrate` every 2 seconds

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register patient/doctor |
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout |
| GET/PUT | `/auth/profile` | Get/update profile |
| POST | `/analyze` | AI health analysis → risk score |
| POST | `/doctors/register` | Register a doctor |
| GET | `/doctors` | List doctors (filter by specialization) |
| POST | `/iot/heartrate` | ESP32 sends BPM data |
| GET | `/iot/heartrate/<id>` | Frontend polls latest BPM |
| POST | `/sos/trigger` | Send emergency SMS via Twilio |
| GET | `/hospitals` | Nearby hospitals (lat/lon) |
| POST | `/reminders/set` | Save reminder config |
| GET | `/audit/<id>` | View patient audit log |
| GET | `/health` | API health check |

---

## 🌍 Multi-Language Support

All UI strings are driven by the `TRANSLATIONS` object in `index.html` (mirrors `i18n.json`).

- **English** 🇬🇧
- **Telugu** 🇮🇳 (తెలుగు)
- **Kannada** 🇮🇳 (ಕನ್ನಡ)

Switch language from the landing page chips or the sidebar dropdown.

---

## 📊 Risk Score Algorithm

The `/analyze` endpoint calculates a **composite health score (0–100)**:

```
score = 100 − (lifestyle_risk × 0.55 + sleep_risk × 0.30 + age_gap × 0.5)
```

**Risk Levels:**
- 🟢 **Low** — Score ≥ 70
- 🟡 **Medium** — Score 45–69
- 🔴 **High** — Score < 45 → triggers SMS alert (if Twilio configured)

**Factors scored:** BMI, smoking, alcohol, stress, sleep, exercise, diet, heart rate, blood pressure, temperature, symptoms

---

## 📱 SMS Alerts (Twilio)

For HIGH risk cases, the system can send SMS via Twilio.

Set in profile (or via the `/analyze` payload):
```json
{
  "twilio_sid": "ACxxxxxxx",
  "twilio_token": "xxxxxxx",
  "twilio_from": "+1xxxxxxxxxx",
  "phone": "+91xxxxxxxxxx"
}
```

---

## 🗄️ Database

Currently uses **in-memory Python dicts** for rapid prototyping.

To use **MongoDB**:
```bash
pip install pymongo
```
Replace `PATIENTS = {}` with `db.patients` collection.

To use **MySQL**:
```bash
pip install flask-sqlalchemy mysql-connector-python
```

---

## ✨ Features

- 🏠 Landing page with Patient / Doctor role selection
- 🌍 Multi-language (English, Telugu, Kannada) with live switching
- 📊 Patient dashboard with 4 metric cards
- 🫀 Live heart rate graph (Chart.js) from ESP32 or mock sensor
- 🔬 Full health analysis form (age, BMI, sleep, BP, symptoms, etc.)
- 🛡️ Animated risk score ring (Low / Medium / High)
- 💡 AI-generated recommendations per risk factor
- 👨‍⚕️ Matched doctor suggestions on high risk
- 🏥 Nearby hospital finder with Google Maps routing
- 📋 Analysis history log
- 👨‍⚕️ Doctor registration and listing
- 📱 SMS alert via Twilio on High risk
- 🔐 Auth with token-based sessions
- 🎨 Modern dark UI with gradients, animations, cards
=======

#For Education purpose ONLY!!
