"""
VitaCore — ESP32 Heart Rate Sensor Mock
Simulates an ESP32 posting BPM values to the Flask backend.

Run:  python sensor_mock.py --patient P12345678 --url http://localhost:5000
Real ESP32 Arduino sketch is provided in sensor/esp32_sketch.ino
"""

import requests, time, math, random, argparse, sys
from datetime import datetime

def simulate_bpm(t, base=72):
    """Realistic BPM: sinusoidal variation + random noise + occasional spikes."""
    wave = math.sin(t / 60) * 6         # slow 60s wave ±6 bpm
    noise = random.gauss(0, 1.5)        # physiological noise
    spike = 20 if random.random() < 0.03 else 0  # 3% chance of brief spike
    return max(45, min(160, round(base + wave + noise + spike)))

def run(patient_id, url, interval_sec=2.0, verbose=True):
    endpoint = f"{url}/iot/heartrate"
    print(f"🫀  VitaCore Sensor Mock  →  patient={patient_id}  endpoint={endpoint}")
    print(f"   Posting every {interval_sec}s  |  Ctrl+C to stop\n")

    t = 0
    session = requests.Session()
    while True:
        bpm = simulate_bpm(t)
        payload = {
            "patient_id": patient_id,
            "heart_rate": bpm,
            "timestamp": datetime.utcnow().isoformat(),
            "sensor": "mock_esp32",
        }
        try:
            r = session.post(endpoint, json=payload, timeout=3)
            status = "✅" if r.status_code == 200 else f"⚠️  {r.status_code}"
            if verbose:
                bar_len = min(bpm // 2, 50)
                bar = "█" * bar_len
                zone = "💚 Normal" if 60<=bpm<=100 else ("💛 Elevated" if bpm<=110 else "🔴 High")
                print(f"  {datetime.now().strftime('%H:%M:%S')}  {bpm:3d} bpm  {bar:<50} {zone}  {status}")
        except requests.exceptions.ConnectionError:
            print(f"  ⛔  Cannot reach {endpoint} — is the backend running?")
        except Exception as e:
            print(f"  ❌  Error: {e}")

        time.sleep(interval_sec)
        t += interval_sec

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VitaCore ESP32 Heart Rate Sensor Mock")
    parser.add_argument("--patient", default="DEMO_PATIENT", help="Patient ID")
    parser.add_argument("--url",     default="http://localhost:5000", help="Backend URL")
    parser.add_argument("--interval",type=float, default=2.0, help="Post interval seconds")
    parser.add_argument("--quiet",   action="store_true", help="Suppress per-reading output")
    args = parser.parse_args()

    try:
        run(args.patient, args.url, args.interval, verbose=not args.quiet)
    except KeyboardInterrupt:
        print("\n\n  Sensor stopped. Goodbye! 👋")
        sys.exit(0)
