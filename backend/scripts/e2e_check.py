import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)

r = c.post("/api/login", json={"email": "arjun.patel@hetu.demo", "password": "ArjunFortis44"})
assert r.status_code == 200, r.text
uid = r.json()["user"]["id"]
h = {"X-User-Id": str(uid)}
pats = c.get("/api/patients", headers=h).json()
print("patients", [(p["name"], p["access_status"]) for p in pats])
priya = next(p for p in pats if "Priya" in p["name"])
res = c.post(
    "/api/diagnoses",
    headers=h,
    json={
        "patient_id": priya["id"],
        "diagnosis_label": "Migraine",
        "full_notes": "Headache with aura",
        "disclose_to_patient": True,
    },
)
print("dx", res.status_code)
assert res.status_code == 200, res.text
print("flags_raised", len(res.json()["flags_raised"]))
flags = c.get("/api/flags", headers=h).json()
print("doctor flags", [(f["status"], f["diagnosis_1"]["diagnosis_label"], f["diagnosis_2"]["diagnosis_label"]) for f in flags])
note = flags[0]
rr = c.post(
    f"/api/flags/{note['id']}/resolve",
    headers=h,
    json={"resolution_note": "Neurology and cardiology findings can coexist; follow both plans."},
)
assert rr.status_code == 200, rr.text
print("resolve", rr.json()["status"])

pr = c.post("/api/login", json={"email": "priya.nair@hetu.demo", "password": "PriyaNair18"})
ph = {"X-User-Id": str(pr.json()["user"]["id"])}
pflags = c.get("/api/flags", headers=ph).json()
print("priya flag", pflags[0]["status"], pflags[0]["pending_review"], pflags[0].get("resolution_note"))

aya = c.post("/api/login", json={"email": "ayaan.khan@hetu.demo", "password": "AyaanKhan12"})
ah = {"X-User-Id": str(aya.json()["user"]["id"])}
bad = c.post(
    "/api/corrections",
    headers=ah,
    json={"patient_id": aya.json()["patient"]["id"], "field": "conditions", "proposed_value": "nope"},
)
print("minor write", bad.status_code, bad.json()["detail"])
assert bad.status_code == 403

far = c.post("/api/login", json={"email": "farah.khan@hetu.demo", "password": "AyaanKhan12"})
fh = {"X-User-Id": str(far.json()["user"]["id"])}
acc = c.get("/api/access-requests", headers=fh).json()
pending = next(a for a in acc if a["status"] == "pending")
ok = c.post(f"/api/access-requests/{pending['id']}/approve", headers=fh)
print("surrogate approve", ok.status_code, ok.json()["status"])
print("E2E OK")
