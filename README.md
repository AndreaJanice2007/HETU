# Hetu

Post-diagnosis reconciliation for healthcare. When two doctors record different diagnosis labels for the same patient, Hetu flags the gap, notifies the clinicians, and tells the patient (or their surrogate) that a review is underway. Hetu does not diagnose. Flags are suggestions; the doctor decides.

## Run locally

Terminal 1 — API (SQLite):

```bash
cd hetu/backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 — UI:

```bash
cd hetu/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

There are no seeded accounts. Create a patient, doctor, or surrogate from **Sign up**. Sign in with that email (or username) and password.

## Comparison module

Label mismatch lives in `backend/app/comparison.py` (`labels_conflict`). v1 is exact match plus `difflib` fuzzy similarity. Swap that module later for Sentence-BERT without touching the rest of the app.
