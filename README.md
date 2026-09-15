# Hetu

Post-diagnosis reconciliation for healthcare. When two doctors record different diagnosis labels for the same patient, Hetu flags the gap, notifies the clinicians, and tells the patient (or their surrogate) that a review is underway. Hetu does not diagnose. Flags are suggestions; the doctor decides.

## Run locally

Terminal 1 — API (SQLite, auto-seeds on first start):

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

To reset seeded demo data, stop the API, delete `backend/hetu.db`, and start it again.

## Demo accounts

Each account has a unique password. There is no signup.

| Person | Role | Email | Password |
|---|---|---|---|
| Dr. Meera Sharma | doctor | `meera.sharma@hetu.demo` | `MeeraApollo91` |
| Dr. Arjun Patel | doctor | `arjun.patel@hetu.demo` | `ArjunFortis44` |
| Priya Nair | adult patient | `priya.nair@hetu.demo` | `PriyaNair18` |
| Ayaan Khan | minor patient | `ayaan.khan@hetu.demo` | `AyaanKhan12` |
| Farah Khan | surrogate (Ayaan's mother) | `farah.khan@hetu.demo` | `FarahKhan27` |

## End-to-end demo

Seeded state: both doctors already have approved access to Priya Nair. Dr. Meera has logged **Hypertension**.

1. Sign in as **Dr. Arjun Patel** (`arjun.patel@hetu.demo` / `ArjunFortis44`).
2. Open Priya Nair and log **Migraine**.
3. A flag appears for both doctors. Priya only sees a pending-review notice (no labels).
4. Resolve the flag with a note.
5. Sign in as **Priya Nair** (`priya.nair@hetu.demo` / `PriyaNair18`) to read the full flag and resolution.

Minor path: **Ayaan Khan** is view-only. Sign in as **Farah Khan** to approve Dr. Arjun's pending access request and perform write-actions on Ayaan's behalf.

## Comparison module

Label mismatch lives in `backend/app/comparison.py` (`labels_conflict`). v1 is exact match plus `difflib` fuzzy similarity. Swap that module later for Sentence-BERT without touching the rest of the app.
