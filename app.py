"""
VitaCore AI Health Monitoring System — Flask Backend
Routes: /analyze, /auth/*, /doctors, /iot/heartrate, /sos, /audit, /hospitals
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json, time, os, hashlib, secrets, math
from datetime import datetime


app = Flask(__name__)

    

app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True, origins=["*"])

# ✅ ADD THIS HERE 👇👇👇
@app.route("/")
def home():
    return jsonify({
        "status": "VitaCore Backend Running 🚀",
        "available_routes": [
            "/auth/register",
            "/auth/login",
            "/analyze",
            "/iot/heartrate",
            "/hospitals"
        ]
    })

@app.route("/iot/heartrate", methods=["POST"])
def receive_heart_rate():
    global latest_heart_rate
    data = request.json
    print("Incoming:",data)

    latest_heart_rate ={
        "bpm":data.get("bpm")
    }
    return {"status": "ok"}
@app.route("/iot/heartrate/latest", methods=["GET"])
def get_latest():
    return latest_heart_rate

# ─── In-Memory Stores (swap with MongoDB/MySQL in production) ─────────────────
PATIENTS       = {}   # username -> user dict
DOCTORS        = {}   # doctor_id -> doctor dict
SESSIONS       = {}   # token -> username
AUDIT_LOG      = {}   # patient_id -> [entries]
HEARTRATE_CACHE= {}   # patient_id -> {heart_rate, timestamp}
REMINDERS      = {}   # patient_id -> config

# ─── Helpers ──────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Auth-Token") or request.args.get("token")
        if not token or token not in SESSIONS:
            return jsonify({"error": "Unauthorized"}), 401
        request.username = SESSIONS[token]
        return f(*args, **kwargs)
    return wrapper

def log_audit(patient_id, event, extra=None):
    if patient_id not in AUDIT_LOG: AUDIT_LOG[patient_id] = []
    entry = {"ts": datetime.utcnow().isoformat(), "event": event}
    if extra: entry.update(extra)
    AUDIT_LOG[patient_id].append(entry)

# ─── Auth ─────────────────────────────────────────────────────────────────────
@app.route("/auth/register", methods=["POST"])
def register():
    d = request.json or {}
    uname = (d.get("username") or "").strip().lower()
    pw    = d.get("password", "")
    name  = d.get("full_name", "")
    role  = d.get("role", "patient")  # patient | doctor

    if not uname or not pw or not name:
        return jsonify({"error": "Username, password and full name required"}), 400
    if len(pw) < 6:
        return jsonify({"error": "Password must be ≥ 6 characters"}), 400
    if uname in PATIENTS:
        return jsonify({"error": "Username taken"}), 409

    pid = "P" + str(int(time.time() * 1000))[-8:]
    PATIENTS[uname] = {
        "password_hash": hash_pw(pw),
        "patient_id": pid, "full_name": name,
        "phone": d.get("phone", ""), "age": d.get("age", 25),
        "gender": d.get("gender", "Male"), "language": d.get("language", "en"),
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
        "profile": {
            "height_cm": 170, "weight_kg": 70, "sleep_hours": 7,
            "daily_steps": 7200, "stress_level": 4, "exercise_freq": "Daily",
            "diet_quality": "Good", "smoker": "No", "alcohol": "None",
            "heart_rate": 72, "systolic_bp": 118, "diastolic_bp": 76,
        },
        "twilio": {"sid":"","token":"","from":"","emergency_phone":"","emergency_name":""},
        "reminders": {"water":True,"workout":True,"diet":True,"medication":False},
        "consent_given": False,
        # Doctor fields (if role == doctor)
        "doctor_info": d.get("doctor_info", {}),
    }
    log_audit(pid, "REGISTRATION", {"username": uname, "role": role})
    token = secrets.token_hex(24)
    SESSIONS[token] = uname
    return jsonify({"status":"registered","token":token,"patient_id":pid,"full_name":name,"language":d.get("language","en"),"role":role})

@app.route("/auth/login", methods=["POST"])
def login():
    d = request.json or {}
    uname = (d.get("username") or "").strip().lower()
    pw    = d.get("password", "")
    user  = PATIENTS.get(uname)
    if not user or user["password_hash"] != hash_pw(pw):
        return jsonify({"error": "Invalid username or password"}), 401
    token = secrets.token_hex(24)
    SESSIONS[token] = uname
    log_audit(user["patient_id"], "LOGIN")
    return jsonify({
        "status":"ok","token":token,
        "patient_id":user["patient_id"],"full_name":user["full_name"],
        "language":user.get("language","en"),"role":user.get("role","patient"),
        "profile":user.get("profile",{}),"twilio":user.get("twilio",{}),
        "reminders":user.get("reminders",{}),
        "consent_given":user.get("consent_given",False),
        "doctor_info":user.get("doctor_info",{}),
    })

@app.route("/auth/logout", methods=["POST"])
@require_auth
def logout():
    SESSIONS.pop(request.headers.get("X-Auth-Token"), None)
    return jsonify({"status":"logged_out"})

@app.route("/auth/profile", methods=["GET","PUT"])
@require_auth
def profile():
    user = PATIENTS[request.username]
    if request.method == "GET":
        return jsonify({k:user[k] for k in ["patient_id","full_name","phone","age","gender","language","profile","twilio","reminders","consent_given","role","doctor_info"] if k in user})
    d = request.json or {}
    for f in ["full_name","phone","age","gender","language"]:
        if f in d: user[f] = d[f]
    if "profile" in d: user["profile"].update(d["profile"])
    if "twilio" in d:  user.setdefault("twilio",{}).update(d["twilio"])
    if "doctor_info" in d: user.setdefault("doctor_info",{}).update(d["doctor_info"])
    return jsonify({"status":"updated"})

# ─── Doctor Registration ───────────────────────────────────────────────────────
@app.route("/doctors/register", methods=["POST"])
def register_doctor():
    d = request.json or {}
    doc_id = "D" + str(int(time.time()*1000))[-8:]
    doc = {
        "doctor_id": doc_id,
        "name": d.get("name",""),
        "hospital": d.get("hospital",""),
        "specialization": d.get("specialization",""),
        "phone": d.get("phone",""),
        "email": d.get("email",""),
        "experience_years": d.get("experience_years", 5),
        "languages": d.get("languages", ["English"]),
        "registered_at": datetime.utcnow().isoformat(),
    }
    DOCTORS[doc_id] = doc
    return jsonify({"status":"registered","doctor_id":doc_id,"doctor":doc})

@app.route("/doctors", methods=["GET"])
def list_doctors():
    spec = request.args.get("specialization","")
    docs = list(DOCTORS.values())
    if spec: docs = [d for d in docs if spec.lower() in d.get("specialization","").lower()]
    # Add seed doctors for demo
    if not docs:
        docs = [
            {"doctor_id":"D00000001","name":"Dr. Priya Sharma","hospital":"Apollo Hospitals","specialization":"Cardiology","phone":"+918042124444","experience_years":12,"languages":["English","Kannada","Hindi"]},
            {"doctor_id":"D00000002","name":"Dr. Rajesh Kumar","hospital":"Manipal Hospital","specialization":"General Medicine","phone":"+918022344444","experience_years":8,"languages":["English","Telugu","Kannada"]},
            {"doctor_id":"D00000003","name":"Dr. Anitha Rao","hospital":"NIMHANS","specialization":"Neurology","phone":"+918046110007","experience_years":15,"languages":["English","Kannada"]},
            {"doctor_id":"D00000004","name":"Dr. Suresh Patel","hospital":"Fortis Hospital","specialization":"Pulmonology","phone":"+918066214444","experience_years":10,"languages":["English","Hindi"]},
        ]
    return jsonify({"doctors":docs})

# ─── Health Analysis ───────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    d      = request.json or {}
    age    = float(d.get("age", 30))
    gender = d.get("gender", "Male")
    height = float(d.get("height_cm", 170))
    weight = float(d.get("weight_kg", 70))
    sleep  = float(d.get("sleep_hours", 7))
    steps  = float(d.get("daily_steps", 7000))
    stress = float(d.get("stress_level", 5))
    ex     = d.get("exercise_freq", "Daily")
    diet   = d.get("diet_quality", "Good")
    smoke  = d.get("smoker", "No")
    alc    = d.get("alcohol", "None")
    hr     = float(d.get("heart_rate", 72))
    sys_bp = float(d.get("systolic_bp", 120))
    dia_bp = float(d.get("diastolic_bp", 80))
    temp   = float(d.get("temperature", 98.6))
    symptoms = d.get("symptoms", [])

    bmi = weight / ((height/100)**2)

    # ── Lifestyle Risk Score ──
    lr = 15
    if bmi > 30: lr += 18
    elif bmi > 25: lr += 10
    elif bmi < 18.5: lr += 6
    if smoke == "Yes": lr += 22
    if alc == "Moderate": lr += 10
    elif alc == "High": lr += 18
    lr += max(0, (stress-5)*3)
    if sleep < 6: lr += 14
    elif sleep < 7: lr += 7
    ex_map = {"Daily":0,"3-5 times/week":5,"1-2 times/week":12,"None":20}
    lr += ex_map.get(ex, 0)
    diet_map = {"Excellent":0,"Good":5,"Average":12,"Poor":20}
    lr += diet_map.get(diet, 0)
    if hr > 100: lr += 8
    if sys_bp > 140: lr += 15
    elif sys_bp > 130: lr += 8
    # Symptoms
    danger_symptoms = ["chest_pain","shortness_of_breath","severe_headache","fainting"]
    sym_bonus = sum(15 for s in symptoms if s in danger_symptoms) + sum(5 for s in symptoms if s not in danger_symptoms)
    lr += min(30, sym_bonus)
    # Temperature
    if temp > 103: lr += 12
    elif temp > 101: lr += 7
    lr = min(98, max(5, lr))

    # ── Sleep Risk ──
    sr = 10
    if sleep < 5: sr += 40
    elif sleep < 6: sr += 28
    elif sleep < 7: sr += 14
    if stress > 7: sr += 18
    elif stress > 5: sr += 8
    sr = min(98, max(5, sr))

    # ── Biological Age ──
    bio_age = age
    if bmi > 30: bio_age += 4
    elif bmi > 25: bio_age += 2
    if smoke == "Yes": bio_age += 5
    if ex == "Daily": bio_age -= 3
    if sleep >= 7: bio_age -= 1
    if stress > 7: bio_age += 3
    bio_age = max(18, round(bio_age))

    # ── Composite Score ──
    base = 100 - (lr * 0.55 + sr * 0.30 + abs(bio_age - age) * 0.5)
    score = max(5, min(98, round(base)))

    # ── Risk Level ──
    if score >= 70: level = "Low"
    elif score >= 45: level = "Medium"
    else: level = "High"

    # ── Recommendations ──
    recs = []
    if lr > 50: recs.append({"icon":"🏃","text":"Increase physical activity to at least 30 min/day"})
    if sleep < 7: recs.append({"icon":"😴","text":"Aim for 7-9 hours of quality sleep each night"})
    if stress > 6: recs.append({"icon":"🧘","text":"Practice mindfulness or breathing exercises daily"})
    if bmi > 25: recs.append({"icon":"🥗","text":"Follow a balanced diet to reach healthy BMI"})
    if smoke == "Yes": recs.append({"icon":"🚭","text":"Smoking significantly increases cardiovascular risk — seek cessation support"})
    if hr > 100: recs.append({"icon":"❤️","text":"Elevated resting heart rate — consult a cardiologist"})
    if sys_bp > 130: recs.append({"icon":"🩺","text":"Blood pressure is elevated — monitor daily and consult physician"})
    if temp > 101: recs.append({"icon":"🌡️","text":"Fever detected — rest, hydrate, and consult a doctor if persistent"})
    if "chest_pain" in symptoms: recs.append({"icon":"🚨","text":"Chest pain reported — seek immediate medical attention"})
    if not recs: recs.append({"icon":"✅","text":"Keep up your healthy lifestyle! Regular checkups are recommended."})

    # ── Matching Doctors ──
    matched_docs = []
    if level == "High":
        all_docs = list(DOCTORS.values()) or [
            {"doctor_id":"D00000001","name":"Dr. Priya Sharma","hospital":"Apollo Hospitals","specialization":"Cardiology","phone":"+918042124444","experience_years":12},
            {"doctor_id":"D00000002","name":"Dr. Rajesh Kumar","hospital":"Manipal Hospital","specialization":"General Medicine","phone":"+918022344444","experience_years":8},
        ]
        matched_docs = all_docs[:3]

    # ── SMS Alert (High Risk) ──
    sms_sent = False
    if level == "High":
        pid = d.get("patient_id","unknown")
        twilio_sid  = d.get("twilio_sid","")
        twilio_tok  = d.get("twilio_token","")
        twilio_from = d.get("twilio_from","")
        phone       = d.get("phone","")
        if twilio_sid and twilio_tok and twilio_from and phone:
            try:
                from twilio.rest import Client
                msg_body = f"🚨 VitaCore Health Alert\nPatient health score: {score}/100 (HIGH RISK)\nHR={int(hr)}bpm | BP={int(sys_bp)}/{int(dia_bp)}\nPlease seek medical attention immediately."
                Client(twilio_sid, twilio_tok).messages.create(body=msg_body, from_=twilio_from, to=phone)
                sms_sent = True
            except: pass

    pid = d.get("patient_id","unknown")
    log_audit(pid, "ANALYSIS", {"score":score,"level":level,"hr":hr,"lr":lr})

    return jsonify({
        "score": score, "risk_level": level, "bmi": round(bmi,1),
        "bio_age": bio_age, "lifestyle_risk": lr, "sleep_risk": sr,
        "recommendations": recs, "matched_doctors": matched_docs,
        "sms_sent": sms_sent,
        "vitals_summary": {"heart_rate":hr,"systolic_bp":sys_bp,"diastolic_bp":dia_bp,"temperature":temp,"sleep":sleep,"bmi":round(bmi,1)},
    })

# ─── IoT / ESP32 ──────────────────────────────────────────────────────────────
@app.route("/iot/heartrate", methods=["POST"])
def receive_heartrate():
    d = request.json or {}
    pid = d.get("patient_id","unknown")
    hr  = d.get("heart_rate")
    if hr is None: return jsonify({"error":"heart_rate missing"}),400
    HEARTRATE_CACHE[pid] = {
        "heart_rate": int(hr),
        "timestamp": d.get("timestamp", datetime.utcnow().isoformat()),
        "received_at": datetime.utcnow().isoformat(),
    }
    return jsonify({"status":"received","heart_rate":int(hr)})

@app.route("/iot/heartrate/<patient_id>", methods=["GET"])
def get_heartrate(patient_id):
    entry = HEARTRATE_CACHE.get(patient_id)
    if not entry: return jsonify({"status":"no_data","heart_rate":None})
    return jsonify({"status":"ok",**entry})

# ─── SOS ─────────────────────────────────────────────────────────────────────
SOS_COOLDOWN = {}

@app.route("/sos/trigger", methods=["POST"])
def sos_trigger():
    d   = request.json or {}
    pid = d.get("patient_id","unknown")
    if not d.get("consent_given"): return jsonify({"error":"Consent required"}),403
    now = time.time()
    if pid in SOS_COOLDOWN and now - SOS_COOLDOWN[pid] < 60:
        return jsonify({"status":"cooldown","remaining":int(60-(now-SOS_COOLDOWN[pid]))})
    SOS_COOLDOWN[pid] = now
    lat = d.get("latitude",12.9716); lon = d.get("longitude",77.5946)
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    sms_sent = False
    if all([d.get("twilio_sid"),d.get("twilio_token"),d.get("twilio_from"),d.get("emergency_phone")]):
        try:
            from twilio.rest import Client
            body = f"🚨 SOS from VitaCore\nPatient: {d.get('patient_name','Patient')}\nLocation: {maps_url}\nTime: {datetime.now().strftime('%d %b %Y %H:%M')}"
            Client(d["twilio_sid"],d["twilio_token"]).messages.create(body=body,from_=d["twilio_from"],to=d["emergency_phone"])
            sms_sent = True
        except: pass
    log_audit(pid,"SOS_TRIGGER",{"sms_sent":sms_sent,"lat":lat,"lon":lon})
    return jsonify({"status":"ok","sms_sent":sms_sent,"maps_url":maps_url})

# ─── Hospitals ─────────────────────────────────────────────────────────────────
HOSPITALS = [
    {"name":"Victoria Hospital","lat":12.9680,"lon":77.5760,"phone":"+918022867806"},
    {"name":"NIMHANS","lat":12.9407,"lon":77.5960,"phone":"+918046110007"},
    {"name":"Manipal Hospital","lat":12.9563,"lon":77.6473,"phone":"+918022344444"},
    {"name":"Apollo Hospitals","lat":12.9121,"lon":77.6446,"phone":"+918042124444"},
    {"name":"Fortis Hospital","lat":12.9010,"lon":77.6038,"phone":"+918066214444"},
]

@app.route("/hospitals", methods=["GET"])
def hospitals():
    lat = float(request.args.get("lat",12.9716))
    lon = float(request.args.get("lon",77.5946))
    hosps = []
    for h in HOSPITALS:
        dlat = math.radians(h["lat"]-lat); dlon = math.radians(h["lon"]-lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(h["lat"]))*math.sin(dlon/2)**2
        hosps.append({**h,"distance_km":round(6371*2*math.asin(math.sqrt(a)),2)})
    hosps.sort(key=lambda x:x["distance_km"])
    return jsonify({"hospitals":hosps})

# ─── Reminders ────────────────────────────────────────────────────────────────
@app.route("/reminders/set", methods=["POST"])
def set_reminders():
    d = request.json or {}; pid = d.get("patient_id","unknown")
    REMINDERS[pid] = {**d,"updated_at":datetime.utcnow().isoformat()}
    log_audit(pid,"REMINDERS_UPDATED")
    return jsonify({"status":"saved"})

# ─── Audit ────────────────────────────────────────────────────────────────────
@app.route("/audit/<patient_id>", methods=["GET"])
def audit(patient_id):
    return jsonify({"entries":AUDIT_LOG.get(patient_id,[])[-100:]})

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok","service":"VitaCore API","time":datetime.utcnow().isoformat(),"patients":len(PATIENTS),"doctors":len(DOCTORS)})

if __name__ == "__main__":
    print("🏥 VitaCore Backend  →  http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)



