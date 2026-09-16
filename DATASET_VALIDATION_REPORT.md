# HETU dataset validation report

Synthetic package generated for prototype / hackathon use. All clinical vignettes are **fictional**. No PhysioNet or n2c2 patient records were downloaded or copied.

## Checklist

| # | Check | Result |
|---|---|---|
| 1 | Exactly 100 synthetic examples | **Pass** — JSON, JSONL, and CSV each have 100 records |
| 2 | Exactly 25 examples per root-cause | **Pass** — doctor_gap 25, patient_gap 25, no_fault 25, intentional_non_disclosure 25 |
| 3 | `training.jsonl` syntax | **Pass** — 100 lines, each `json.loads`; assistant content is JSON with `root_cause`, `reasoning`, `appropriate_response` only |
| 4 | `synthetic_clinical_contradictions.json` syntax | **Pass** — one JSON array, IDs `HETU_SYN_001` … `HETU_SYN_100` sequential |
| 5 | CSV structure and row count | **Pass** — header plus 100 rows; columns match spec; pandas `read_csv` shape (100, 8) |
| 6 | Duplicate or near-duplicate contradictions | **Pass** — 100 unique `contradiction` strings |
| 7 | `root_cause` only the four allowed values | **Pass** |
| 8 | No real patient information | **Pass** — synthetic Adult A / Specialist A–B vignettes; `real_datasets_reference.json` is metadata only |
| 9 | No invented personal names or identifiers | **Pass** — no phone/MRN/SSN-like patterns; no `Dr. First Last` style personal names in fields |
| 10 | intentional_non_disclosure is contextual, not mere missingness | **Pass** — examples 076–100 cite documented staged disclosure, policy, ethics, confidentiality, blinding, or Adult A request |
| 11 | no_fault includes diagnostic evolution | **Pass** — serial troponin, cultures, CT vs radiograph, biopsy vs excision, interval EF change, assay/method differences, hemolysis/clumping |
| 12 | doctor_gap vs patient_gap distinguishable | **Pass** — 001–025 use in-chart accessible facts; 026–050 use information not in the record (forgotten, misunderstood, withheld by Adult A) |
| 13 | Responses blame-aware and clinically cautious | **Pass** — responses defer to clinician review; avoid definitive disease labeling; no autonomous treatment orders |
| 14 | Final counts recorded | **Pass** — this report |

## File inventory

```
hetu/training/training.jsonl
hetu/training/synthetic_clinical_contradictions.json
hetu/training/synthetic_clinical_contradictions.csv
hetu/training/real_datasets_reference.json
hetu/training/DATASET_README.md
hetu/scripts/real_dataset_adapter_example.py
hetu/DATASET_VALIDATION_REPORT.md
```

## Real-world data

Five official dataset **references** are listed. Restricted corpora were **not** fetched. The MIMIC-IV demo is noted as open schema practice **without** notes.

## Residual limitations

Labels are author-assigned, not a multi-clinician consensus. English-language vignettes. Not connected to the live demo’s `Label mismatch` flag unless integrated later.
