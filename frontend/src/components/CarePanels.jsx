import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { CtaButton, EmptyState, Field, GhostButton, formatWhen, inputClass } from "../ui";

const EMPTY_RECORDS = "No records yet — your history will appear here after your first consultation";

export function ReportMedia({ fileUrl, hasImage, filename }) {
  const [src, setSrc] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!fileUrl) return undefined;
    let objectUrl = "";
    let cancelled = false;
    api
      .reportFile(fileUrl)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setSrc(url);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileUrl]);

  if (!fileUrl) return null;
  if (error) return <p className="mt-2 text-xs text-charcoal/45">{error}</p>;
  if (hasImage && src) {
    return (
      <img
        src={src}
        alt={filename || "Scanned report"}
        className="mt-3 max-h-72 w-full rounded-[10px] bg-white object-contain ring-1 ring-charcoal/8"
      />
    );
  }
  if (!hasImage && src) {
    return (
      <a href={src} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm text-mint">
        Open attached file{filename ? ` (${filename})` : ""}
      </a>
    );
  }
  return fileUrl ? <p className="mt-2 text-xs text-charcoal/45">Loading attachment…</p> : null;
}

function asTimeline(diagnoses = []) {
  return diagnoses.map((dx) => ({
    id: `dx-${dx.id}`,
    type: "diagnosis",
    kind: "Diagnosis",
    date: dx.timestamp,
    doctor_name: dx.doctor?.name,
    title: dx.diagnosis_label || "On file",
    summary: dx.full_notes || dx.diagnosis_label,
    report_id: null,
  }));
}

export function RecordsTimeline({ items, diagnoses, empty = EMPTY_RECORDS }) {
  const list = Array.isArray(items) ? items : asTimeline(diagnoses);
  if (!list.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ol className="relative ml-2 space-y-5 border-l border-charcoal/10 pl-6">
      {list.map((row) => (
        <li key={row.id} className="relative">
          <span
            className={`absolute -left-[31px] top-4 h-2.5 w-2.5 rounded-full ${
              row.type === "report" ? "bg-mint" : "bg-charcoal/25"
            }`}
          />
          <article className="rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-charcoal/40">{row.kind}</p>
              <span className="text-xs text-charcoal/45">{formatWhen(row.date) || "On file"}</span>
            </div>
            <h3 className="mt-1 text-base font-semibold">{row.title}</h3>
            <p className="mt-1 text-sm text-charcoal/55">{row.doctor_name || "Your record"}</p>
            {row.summary ? <p className="mt-3 text-sm leading-relaxed text-charcoal/80">{row.summary}</p> : null}
            <ReportMedia fileUrl={row.file_url} hasImage={row.has_image} filename={row.original_filename} />
          </article>
        </li>
      ))}
    </ol>
  );
}

export function ReportUpload({ canWrite, patientId, doctors, conditions, onUploaded, viewerRole = "patient" }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("type");
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [issue, setIssue] = useState(conditions?.[0] || "");
  const [customIssue, setCustomIssue] = useState("");
  const [reportDate, setReportDate] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [scanReady, setScanReady] = useState(false);

  if (!canWrite) return null;
  const isDoctor = viewerRole === "doctor";

  async function submit(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    const related = (issue === "__other" ? customIssue : issue).trim();
    if (!notes.trim() && !file) {
      setError("Type the report, upload a file, or scan a page.");
      return;
    }
    const form = new FormData();
    if (file) form.append("file", file);
    if (notes.trim()) form.append("notes", notes.trim());
    if (related) form.append("related_issue", related);
    form.append("source", mode);
    if (reportDate) form.append("report_date", reportDate);
    if (!isDoctor && doctorId) form.append("doctor_id", doctorId);
    if (patientId) form.append("patient_id", String(patientId));
    setBusy(true);
    try {
      const result = await onUploaded(form);
      setFile(null);
      setNotes("");
      setOpen(false);
      setInfo(result?.conversation ? "Logged. Your doctors are reviewing this together." : "Report saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function captureScan() {
    const video = document.getElementById("hetu-report-scan");
    if (!video || !video.srcObject) {
      setError("Allow camera access to scan, or upload a photo instead.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) {
        setError("Could not capture the scan.");
        return;
      }
      setFile(new File([blob], `scan-${Date.now()}.jpg`, { type: "image/jpeg" }));
      stopScan();
    }, "image/jpeg", 0.92);
  }

  async function startScan() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
      const video = document.getElementById("hetu-report-scan");
      if (video) {
        video.srcObject = stream;
        await video.play();
        setScanReady(true);
      }
    } catch {
      setError("Camera is unavailable. Use Scan file to pick a photo instead.");
    }
  }

  function stopScan() {
    const video = document.getElementById("hetu-report-scan");
    const stream = video?.srcObject;
    if (stream) stream.getTracks().forEach((track) => track.stop());
    if (video) video.srcObject = null;
    setScanReady(false);
  }

  function chooseMode(next) {
    if (mode === "scan") stopScan();
    setMode(next);
    setFile(null);
  }

  return (
    <div className="mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">{isDoctor ? "Add a report" : "Your records"}</h2>
          <p className="mt-1 text-sm text-charcoal/55">
            Type the report, upload a file, or scan a page. Images stay visible on the record.
          </p>
        </div>
        <CtaButton
          type="button"
          onClick={() => {
            if (open && mode === "scan") stopScan();
            setOpen((v) => !v);
          }}
        >
          {open ? "Close" : "Add report"}
        </CtaButton>
      </div>
      {info ? <p className="mt-3 text-sm text-mint">{info}</p> : null}
      {open ? (
        <form className="mt-5 grid gap-4 rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8" onSubmit={submit}>
          <div className="flex flex-wrap gap-2">
            {[
              ["type", "Type"],
              ["upload", "Upload file"],
              ["scan", "Scan"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => chooseMode(id)}
                className={`rounded-full px-3 py-1.5 text-sm ${
                  mode === id ? "bg-mint text-white" : "bg-white text-charcoal ring-1 ring-charcoal/15"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {mode === "type" ? (
            <Field label="Type the report">
              <textarea
                className={`${inputClass} min-h-32`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Write findings, prescriptions, or what the page says."
              />
            </Field>
          ) : null}
          {mode === "upload" ? (
            <Field label="Upload any file">
              <input className={inputClass} type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <p className="mt-1 text-xs text-charcoal/45">PDF, Word, images, text, or another file type. Max 12 MB.</p>
            </Field>
          ) : null}
          {mode === "scan" ? (
            <div className="grid gap-3">
              <video id="hetu-report-scan" className="h-48 w-full rounded-[10px] bg-charcoal/10 object-cover" playsInline muted />
              <div className="flex flex-wrap gap-2">
                <GhostButton type="button" onClick={startScan}>
                  Open camera
                </GhostButton>
                <CtaButton type="button" onClick={captureScan} disabled={!scanReady}>
                  Capture page
                </CtaButton>
              </div>
              <Field label="Or choose a scanned photo / PDF">
                <input
                  className={inputClass}
                  type="file"
                  accept="image/*,.pdf,application/pdf"
                  capture="environment"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </Field>
            </div>
          ) : null}
          {file ? <p className="text-sm text-charcoal/60">Attached: {file.name}</p> : null}
          <Field label="Related issue or symptom">
            <select className={inputClass} value={issue} onChange={(e) => setIssue(e.target.value)}>
              <option value="">Select or add</option>
              {(conditions || []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
              <option value="__other">Something else…</option>
            </select>
          </Field>
          {issue === "__other" ? (
            <Field label="Describe the issue">
              <input className={inputClass} value={customIssue} onChange={(e) => setCustomIssue(e.target.value)} />
            </Field>
          ) : null}
          <Field label="Date of report">
            <input className={inputClass} type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
          </Field>
          {!isDoctor ? (
            <Field label="Give this report to a doctor">
              <select className={inputClass} value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
                <option value="">Choose a doctor</option>
                {(doctors || []).map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.name} · {doc.specialty}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          {error ? <p className="text-sm text-severity-high">{error}</p> : null}
          <div className="flex gap-3">
            <CtaButton type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save report"}
            </CtaButton>
            <GhostButton
              type="button"
              onClick={() => {
                stopScan();
                setOpen(false);
              }}
            >
              Cancel
            </GhostButton>
          </div>
        </form>
      ) : null}
    </div>
  );
}

export function ConversationStatusCard({ conversation }) {
  if (!conversation) return null;
  return (
    <article className="rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-mint/30">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-mint">Care team update</p>
      <h3 className="mt-2 text-lg font-semibold">{conversation.patient_status}</h3>
      <p className="mt-1 text-sm text-charcoal/55">{conversation.issue_type}</p>
      {conversation.patient_conclusion ? (
        <p className="mt-3 text-sm leading-relaxed text-charcoal/80">{conversation.patient_conclusion}</p>
      ) : (
        <p className="mt-3 text-sm text-charcoal/60">No clinical verdict is shown here — this is only a status update.</p>
      )}
    </article>
  );
}

export function ReconciliationCard({ flag }) {
  const first = flag.diagnosis_1;
  const second = flag.diagnosis_2;
  return (
    <article className="rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-charcoal/40">Review note</p>
          <h3 className="mt-1 text-lg font-semibold">{flag.patient_status_label || "Your doctors are looking at two notes together"}</h3>
        </div>
        <span className="inline-flex rounded-full bg-mint/15 px-2.5 py-1 text-xs font-medium text-mint">
          {flag.patient_next_step || "Your doctors are discussing this"}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {[first, second].map((dx, index) => (
          <div key={dx?.id || index} className="rounded-[10px] bg-white p-3 ring-1 ring-charcoal/8">
            <p className="text-sm font-semibold">{dx?.doctor?.name || "Doctor"}</p>
            <p className="mt-1 text-sm text-charcoal/80">{dx?.diagnosis_label || "On file"}</p>
            <p className="mt-1 text-xs text-charcoal/45">{formatWhen(dx?.timestamp)}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm leading-relaxed text-charcoal/75">
        {flag.patient_explanation || "Two notes differ slightly. Your doctors are looking at this together."}
      </p>
      {flag.status === "resolved" && flag.resolution_note ? (
        <p className="mt-3 rounded-[10px] bg-mint/10 px-3 py-2 text-sm text-charcoal/80">{flag.resolution_note}</p>
      ) : null}
    </article>
  );
}

export function GapResponseCard({ flag, canWrite, onRespond }) {
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);
  const considered = flag.diagnosis_2?.diagnosis_label || flag.diagnosis_1?.diagnosis_label || "this";
  const doctorName = flag.diagnosis_2?.doctor?.name || flag.diagnosis_1?.doctor?.name || "your doctor";
  if (flag.root_cause !== "patient_gap") return null;
  if (flag.gap_answer) {
    return (
      <article className="rounded-xl bg-offwhite p-5 ring-1 ring-charcoal/8">
        <p className="text-sm text-charcoal/60">You already answered this question ({flag.gap_answer}).</p>
      </article>
    );
  }
  if (!canWrite) return null;

  async function respond(answer) {
    setBusy(true);
    try {
      await onRespond(flag.id, { answer, detail: answer === "detail" ? detail : "" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-charcoal/40">Quick question</p>
      <h3 className="mt-2 text-lg font-semibold">
        {doctorName}&apos;s assessment considered {considered} — is this something you&apos;d mentioned before?
      </h3>
      <div className="mt-4 flex flex-wrap gap-2">
        <CtaButton type="button" disabled={busy} onClick={() => respond("yes")}>
          Yes
        </CtaButton>
        <GhostButton type="button" disabled={busy} onClick={() => respond("no")}>
          No
        </GhostButton>
      </div>
      <Field label="Add detail">
        <textarea className={`${inputClass} mt-3 min-h-20`} value={detail} onChange={(e) => setDetail(e.target.value)} />
      </Field>
      <GhostButton type="button" className="mt-3" disabled={busy || !detail.trim()} onClick={() => respond("detail")}>
        Send detail
      </GhostButton>
    </article>
  );
}

export function PatientRecordsDashboard({
  canWrite,
  patient,
  timeline,
  flags,
  conversations,
  doctors,
  onUpload,
  onGap,
  viewerRole = "patient",
}) {
  const issueOptions = useMemo(() => {
    const fromConditions = patient?.conditions || [];
    const fromTimeline = (timeline || []).map((row) => row.title).filter(Boolean);
    return [...new Set([...fromConditions, ...fromTimeline])];
  }, [patient?.conditions, timeline]);

  return (
    <div className="space-y-10">
      <ReportUpload
        canWrite={canWrite}
        patientId={patient?.id}
        doctors={doctors}
        conditions={issueOptions}
        onUploaded={onUpload}
        viewerRole={viewerRole}
      />
      {conversations?.length ? (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Together with your doctors</h2>
          {conversations.map((row) => (
            <ConversationStatusCard key={row.id} conversation={row} />
          ))}
        </section>
      ) : null}
      {flags?.length ? (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Notes your doctors are reviewing</h2>
          {flags.map((flag) => (
            <div key={flag.id} className="space-y-3">
              <ReconciliationCard flag={flag} />
              <GapResponseCard flag={flag} canWrite={canWrite} onRespond={onGap} />
            </div>
          ))}
        </section>
      ) : null}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Timeline</h2>
        <RecordsTimeline items={timeline} empty={EMPTY_RECORDS} />
      </section>
    </div>
  );
}

export function ExplainerView({ explainer }) {
  if (!explainer) return <EmptyState>Loading explanation…</EmptyState>;
  const plain = [explainer.audience, explainer.flags, explainer.diagnoses].filter(Boolean).join(" ");

  return (
    <div className="max-w-2xl">
      <span className="mb-3 inline-flex rounded-full bg-mint/15 px-2.5 py-1 text-xs font-medium text-mint">
        Simplified by AI
      </span>
      <p className="text-base leading-7 text-charcoal">{plain}</p>
      <p className="mt-4 text-sm text-charcoal/50">{explainer.disclaimer}</p>
    </div>
  );
}

export function ConsentCenter({ access, canWrite, onDecide }) {
  if (!access.length) {
    return <EmptyState>No requests to view previous treatment yet.</EmptyState>;
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-charcoal/55">
        Doctors can receive the reports you send them without a request. Approval here is only for previous treatment.
      </p>
      {!canWrite ? (
        <p className="text-sm text-charcoal/50">Access approvals are handled by the surrogate.</p>
      ) : null}
      {access.map((req) => (
        <article
          key={req.id}
          className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8"
        >
          <div>
            <div className="font-semibold">{req.doctor.name}</div>
            <div className="text-sm text-charcoal/50">
              {req.doctor.specialty} · {req.doctor.hospital}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                req.status === "approved"
                  ? "bg-mint/15 text-mint"
                  : req.status === "denied"
                    ? "bg-charcoal/10 text-charcoal/60"
                    : "bg-[#e6e6e3] text-charcoal/55"
              }`}
            >
              {req.status}
            </span>
            {canWrite && req.status === "pending" ? (
              <>
                <button
                  type="button"
                  className="rounded-[10px] bg-mint px-3 py-2 text-sm font-medium text-offwhite"
                  onClick={() => onDecide(req.id, true)}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="rounded-[10px] border border-charcoal/20 px-3 py-2 text-sm text-charcoal"
                  onClick={() => onDecide(req.id, false)}
                >
                  Deny
                </button>
              </>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}

export function CorrectionForm({ canWrite, field, setField, proposed, setProposed, corrections, onSubmit }) {
  if (!canWrite) {
    return <EmptyState>View-only — your surrogate submits corrections.</EmptyState>;
  }
  return (
    <div className="mx-auto max-w-xl space-y-8">
      <p className="text-sm text-charcoal/55">
        Flag something outdated in your own record. It goes to the doctors who already have access.
      </p>
      <form className="grid gap-5" onSubmit={onSubmit}>
        <label className="grid gap-1.5 text-sm font-medium">
          Field
          <select
            className="w-full rounded-[10px] border border-charcoal/15 bg-white px-3 py-2.5"
            value={field}
            onChange={(e) => setField(e.target.value)}
          >
            <option value="conditions">Conditions</option>
            <option value="medications">Medications</option>
          </select>
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          Suggested update
          <textarea
            className="min-h-28 w-full rounded-[10px] border border-charcoal/15 bg-white px-3 py-2.5"
            value={proposed}
            onChange={(e) => setProposed(e.target.value)}
            required
          />
        </label>
        <button type="submit" className="rounded-[10px] bg-mint px-4 py-2.5 text-sm font-medium text-offwhite">
          Submit suggestion
        </button>
      </form>
      <div>
        <h3 className="mb-3 text-sm font-semibold">Previous suggestions</h3>
        {corrections.length === 0 ? (
          <p className="text-sm text-charcoal/45">None yet.</p>
        ) : (
          corrections.map((c) => (
            <p key={c.id} className="mb-2 text-sm">
              <span className="text-charcoal/45">{c.field}:</span> {c.proposed_value}
            </p>
          ))
        )}
      </div>
    </div>
  );
}
