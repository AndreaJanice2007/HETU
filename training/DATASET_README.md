# HETU synthetic contradiction dataset

## 1. Dataset purpose

This package supports a Medithon prototype of HETU, a clinical decision-support helper that:

- flags apparent contradictions between two specialist findings plus context
- assigns **exactly one** of four root-cause labels
- drafts a cautious, blame-aware response

It is for **educational / hackathon / prototype** use. It is not a medical device, not a diagnosis engine, and not a substitute for a qualified clinician.

## 2. Synthetic vs real dataset distinction

| Package file | What it is | What it is not |
|---|---|---|
| `synthetic_clinical_contradictions.json` / `.csv` / `training.jsonl` | **100 fictional** examples. IDs `HETU_SYN_001`–`100`. People are referred to as Adult A and Specialist A/B. | Not real patients. Not de-identified EHR extracts. |
| `real_datasets_reference.json` | **Metadata only** for official public/credentialed research corpora (MIMIC-IV, MIMIC-IV-Note, eICU, MIMIC-IV demo, n2c2). | Does **not** contain notes, labs, or rows from those corpora. |

Do not mix restricted real notes into `training.jsonl`.

## 3. Four root-cause definitions

1. **doctor_gap** — Important information appears to have been in the record or reasonably accessible, but was missed, misunderstood, incorrectly documented, or insufficiently communicated.
2. **patient_gap** — Relevant information may not have been available because Adult A did not disclose it, forgot it, misunderstood a question, or did not provide it when asked.
3. **no_fault** — The apparent contradiction can reasonably be explained by diagnostic evolution, new evidence, timing, different contexts, measurement variation, or genuine uncertainty.
4. **intentional_non_disclosure** — Information appears intentionally withheld from Adult A **for a documented communication, policy, confidentiality, or compassionate reason**. Missing information alone is not this class.

Do not invent additional categories.

## 4. Number of examples per category

| root_cause | count |
|---|---|
| doctor_gap | 25 |
| patient_gap | 25 |
| no_fault | 25 |
| intentional_non_disclosure | 25 |
| **Total** | **100** |

IDs: `HETU_SYN_001`–`025` doctor_gap; `026`–`050` patient_gap; `051`–`075` no_fault; `076`–`100` intentional_non_disclosure.

## 5. Clinical scenario coverage

Examples include (among others): medication history and reconciliation, allergies, blood pressure, diabetes/A1c, laboratory values, imaging, symptoms, surgical history, family history, prior diagnoses, medication changes, specialist-to-specialist handoff, incomplete documentation, conflicting terminology, diagnostic evolution, newly available tests, measurement differences, inconclusive sampling, non-disclosure, forgotten history, misunderstood questions, and documented compassionate or policy-based non-disclosure.

## 6. Edge cases included

- Chart facts that **look unused** (doctor_gap) versus **not in the chart** (patient_gap).
- Contradictions that **look like a miss** but are **serial tests, different protocols, hemolysis, clumping, or later evolution** (no_fault).
- Compatible statements about **different dates, settings, assays, or stages**.
- Intentional non-disclosure **only** when a policy, ethics note, staged counseling plan, or documented preference is in context.

## 7. Potential dataset biases

- English, adult-heavy vignettes; limited obstetrics/pediatrics (a few staged examples only).
- Single fictional health-system assumption for many doctor_gap cases.
- Uneven specialty mix (more cardio/endo/imaging than rare diseases).
- Intentional_non_disclosure over-represents oncology, genetics, and ICU communication policies.
- Labels are **author-assigned for a prototype**, not adjudicated by a clinical panel.

## 8. Limitations

- 100 examples cannot cover all of clinical medicine.
- No gold-standard inter-rater reliability study.
- Not validated against real EHR contradiction rates.
- Responses are templates for cautious language, not care plans.
- The live HETU demo app still uses a simpler “label mismatch” flag and is **not** wired to these four classes unless you integrate them later.

## 9. Safety considerations

- Fictional IDs and role labels only (Adult A, Specialist A).
- Cautious verbs: may indicate, could represent, requires clinician review, consistent with.
- No definitive diagnoses; no instruction to treat autonomously.
- Do not use model output as a clinical order.
- Do not train on or redistribute restricted PhysioNet/n2c2 notes.

## 10. How to use `training.jsonl` for supervised fine-tuning

Each line is a chat example:

- `system`: HETU decision-support role (no definitive diagnoses).
- `user`: Specialist A/B findings, context, contradiction.
- `assistant`: **only** a JSON object with `root_cause`, `reasoning`, `appropriate_response`.

Fine-tune a chat model on these messages. At inference, parse the assistant JSON and reject any `root_cause` outside the four strings.

Example (OpenAI-style SFT / chat completions JSONL) is already the file format. For Hugging Face `trl` SFT, map `messages` to your tokenizer’s chat template.

## 11. How to use the real datasets for research/evaluation

1. Read `real_datasets_reference.json`.
2. Complete **official** credentialing (PhysioNet CITI + DUA; n2c2 portal DUA).
3. Keep real notes in an approved environment.
4. Use `../scripts/real_dataset_adapter_example.py` as a **schema reminder** only.
5. Evaluate extractors (meds, problems, timestamps) on authorized data. **Do not** assume MIMIC or n2c2 contain HETU’s four labels—you would need a new annotation protocol.

The MIMIC-IV **demo** is open schema practice and **excludes notes**.

## 12. Why real clinical data should NOT simply be copied into the fine-tuning dataset

- DUAs typically **forbid redistribution** (including GitHub and shared JSONL).
- De-identification is not permission to republish notes.
- Real notes lack HETU root-cause labels; naive copy would leak PHI-risk text without teaching the four-class task.
- Mixing real notes with synthetic SFT can hide leakage and consent violations.
- Fine-tuning on restricted text can embed sensitive patterns even if IDs are stripped.

Use synthetic `training.jsonl` for the public prototype. Use authorized corpora in a private research setting with a separate IRB/DUA workflow.

## 13. Recommended train / validation / test split

Target **80% / 10% / 10%** (80 / 10 / 10 examples) **after grouping**, not a random shuffle of near-duplicates.

**Group first** (keep a scenario family in one split):

- Medication reconciliation / fill-history
- Allergy and contrast
- Imaging vs history
- Labs, hemolysis, clumping, serial biomarkers
- Diagnostic evolution (cultures, CT vs radiograph, biopsy vs excision)
- Patient wording / forgotten / withheld history
- Documented disclosure holds (portal, ethics, adolescent confidentiality, trial blinding)

Then assign **whole groups** to train, val, or test so a “missed ACE-inhibitor allergy” style case is not in both train and test.

Suggested ID bands (illustrative, adjust if you regroup):

- **Train (80):** `HETU_SYN_001`–`020`, `026`–`045`, `051`–`070`, `076`–`095`
- **Validation (10):** `021`–`023`, `046`–`047`, `071`–`072`, `096`–`097`
- **Test (10):** `024`–`025`, `048`–`050`, `073`–`075`, `098`–`100`

This keeps most of each class in train while holding out later IDs in each class for test/val. Re-check that no two splits share near-identical contradictions before reporting metrics.

If you need a strict 25-per-class balance inside each split, use stratified sampling **within groups**, not across paraphrases of the same vignette.
