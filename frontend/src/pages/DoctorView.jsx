import { useEffect, useMemo, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import AppShell from "../components/AppShell";
import SendReport from "../components/SendReport";
import { buildReport } from "../medreaStore";
import {
  AccessStatus,
  Card,
  CtaButton,
  EmptyState,
  Field,
  GhostButton,
  SEVERITY_RANK,
  SeverityBadge,
  StatusPill,
  formatWhen,
  inputClass,
} from "../ui";

export default function DoctorView() {
  const { session } = useAuth();
  const [params, setParams] = useSearchParams();
  const [patients, setPatients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [diagnoses, setDiagnoses] = useState([]);
  const [flags, setFlags] = useState([]);
  const [labels, setLabels] = useState([]);
  const [reasons, setReasons] = useState([]);
  const [label, setLabel] = useState("Migraine");
  const [fullNotes, setFullNotes] = useState("");
  const [disclose, setDisclose] = useState(true);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [sort, setSort] = useState("severity");
  const [filter, setFilter] = useState("active");
  const [activeFlag, setActiveFlag] = useState(null);
  const [note, setNote] = useState("");

  async function reload(patientId) {
    const [plist, fl, catalog] = await Promise.all([api.patients(), api.flags(), api.catalog()]);
    setPatients(plist);
    setFlags(fl);
    setLabels(catalog.labels || []);
    setReasons(catalog.disclosure_reasons || []);
    const current =
      plist.find((p) => p.id === Number(patientId)) ||
      plist.find((p) => p.id === selected?.id) ||
      plist[0];
    const flagId = params.get("flag");
    if (flagId) {
      const found = fl.find((f) => String(f.id) === String(flagId));
      if (found) {
        setActiveFlag(found);
        const flagged = plist.find((p) => p.id === found.patient_id);
        if (flagged) {
          setSelected(flagged);
          if (flagged.access_status === "approved") {
            setDiagnoses(await api.diagnoses(flagged.id));
          } else {
            setDiagnoses([]);
          }
          return;
        }
      }
    }
    setSelected(current || null);
    if (current?.access_status === "approved") {
      setDiagnoses(await api.diagnoses(current.id));
    } else {
      setDiagnoses([]);
    }
  }

  useEffect(() => {
    reload().catch((err) => setError(err.message));
  }, []);

  const visibleFlags = useMemo(() => {
    const filtered = flags.filter((f) => {
      if (filter === "active") return f.status !== "resolved";
      if (filter === "all") return true;
      return f.status === filter;
    });
    return [...filtered].sort((a, b) => {
      if (sort === "status") return a.status.localeCompare(b.status);
      return (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9);
    });
  }, [flags, sort, filter]);

  async function choose(patient) {
    setSelected(patient);
    setInfo("");
    setError("");
    if (patient.access_status === "approved") setDiagnoses(await api.diagnoses(patient.id));
    else setDiagnoses([]);
  }

  async function requestAccess() {
    try {
      await api.requestAccess(selected.id);
      setInfo("Access requested.");
      await reload(selected.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function logDiagnosis(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    try {
      const result = await api.logDiagnosis({
        patient_id: selected.id,
        diagnosis_label: label,
        full_notes: fullNotes,
        disclose_to_patient: disclose,
        disclosure_reason: disclose ? null : reason,
      });
      const raised = result.flags_raised?.length || 0;
      setInfo(
        raised
          ? `Saved. Hetu raised ${raised} flag${raised === 1 ? "" : "s"}.`
          : "Saved. No label conflict detected."
      );
      setFullNotes("");
      await reload(selected.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function resolve() {
    try {
      await api.resolveFlag(activeFlag.id, note);
      setNote("");
      setActiveFlag(null);
      setParams({});
      await reload(selected?.id);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!session?.user) return <Navigate to="/" replace />;
  if (session.user.role !== "doctor") {
    return <Navigate to={session.user.role === "surrogate" ? "/surrogate" : "/patient"} replace />;
  }

  const approved = selected?.access_status === "approved";

  return (
    <AppShell title={`${session.doctor?.specialty} · ${session.doctor?.hospital}`} role="doctor">
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Flags</h1>
            <p className="mt-1 text-sm text-charcoal/50">Suggestions only. Final judgment stays with you.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SendReport
              userId={session.user.id}
              report={buildReport({
                role: "doctor",
                patientName: selected?.name,
                diagnoses,
                flags: selected ? flags.filter((f) => f.patient_id === selected.id) : flags,
                access: selected
                  ? [{ doctor: session.user.name, status: selected.access_status }]
                  : [],
              })}
            />
            <select
              className="rounded-[10px] border border-charcoal/15 bg-white px-3 py-2 text-sm"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="severity">Sort by severity</option>
              <option value="status">Sort by status</option>
            </select>
            <select
              className="rounded-[10px] border border-charcoal/15 bg-white px-3 py-2 text-sm"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="active">Active</option>
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="under_review">Under review</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
        {visibleFlags.length === 0 ? (
          <Card>
            <EmptyState>
              {filter === "active"
                ? "No active flags — all reviewed patient records are consistent"
                : "No flags in this view."}
            </EmptyState>
          </Card>
        ) : (
          <div className="overflow-hidden rounded-xl bg-offwhite shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
            {visibleFlags.map((flag) => (
              <button
                type="button"
                key={flag.id}
                onClick={() => {
                  setActiveFlag(flag);
                  setParams({ flag: String(flag.id) });
                  if (flag.status === "open") api.reviewFlag(flag.id).catch(() => {});
                }}
                className="flex w-full flex-wrap items-center gap-4 border-b border-charcoal/8 px-5 py-4 text-left last:border-0 hover:bg-white/60"
              >
                <SeverityBadge severity={flag.severity || "high"} />
                <div className="min-w-[10rem] flex-1">
                  <div className="font-semibold">{flag.patient_name}</div>
                  <div className="text-sm text-charcoal/50">{flag.root_cause || "Label mismatch"}</div>
                </div>
                <StatusPill status={flag.status} />
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="mt-12 grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Patients</h2>
          <div className="space-y-2">
            {patients.map((p) => (
              <button
                type="button"
                key={p.id}
                onClick={() => choose(p)}
                className={`flex w-full items-center justify-between rounded-[10px] px-3 py-3 text-left ${
                  selected?.id === p.id ? "bg-white ring-1 ring-mint" : "hover:bg-white/70"
                }`}
              >
                <span>
                  <span className="block font-medium">{p.name}</span>
                  <span className="text-xs text-charcoal/45">
                    Age {p.age}
                    {p.is_minor ? " · minor" : ""}
                  </span>
                </span>
                <AccessStatus status={p.access_status} />
              </button>
            ))}
          </div>
        </Card>

        <Card>
          {selected ? (
            <>
              <h2 className="text-lg font-semibold">{selected.name}</h2>
              <p className="mt-1 text-sm text-charcoal/50">
                {selected.is_minor ? "Minor — surrogate approves access." : "Adult patient."}
              </p>
              {approved ? (
                <form className="mt-6 grid max-w-lg gap-5" onSubmit={logDiagnosis}>
                  <Field label="Diagnosis label">
                    <select className={inputClass} value={label} onChange={(e) => setLabel(e.target.value)}>
                      {labels.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Clinical notes">
                    <textarea
                      className={`${inputClass} min-h-24`}
                      value={fullNotes}
                      onChange={(e) => setFullNotes(e.target.value)}
                    />
                  </Field>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-medium">Disclose directly to patient?</span>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={disclose}
                      onClick={() => setDisclose((v) => !v)}
                      className={`relative h-7 w-12 rounded-full transition-colors ${disclose ? "bg-mint" : "bg-charcoal/20"}`}
                    >
                      <span
                        className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform ${
                          disclose ? "left-5" : "left-0.5"
                        }`}
                      />
                    </button>
                  </div>
                  <div
                    className={`grid overflow-hidden transition-all duration-300 ${
                      disclose ? "max-h-0 opacity-0" : "max-h-40 opacity-100"
                    }`}
                  >
                    <Field label="Disclosure reason">
                      <select className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} required={!disclose}>
                        <option value="">Select a reason</option>
                        {reasons.map((item) => (
                          <option key={item}>{item}</option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <CtaButton type="submit" className="w-full">
                    Save diagnosis
                  </CtaButton>
                  {diagnoses.length ? (
                    <div className="text-sm text-charcoal/55">
                      {diagnoses.map((dx) => (
                        <p key={dx.id}>
                          {dx.diagnosis_label} · {dx.doctor?.name}
                          {dx.disclose_to_patient ? "" : " · surrogate notified"}
                        </p>
                      ))}
                    </div>
                  ) : null}
                </form>
              ) : (
                <div className="mt-6 space-y-4">
                  <p className="text-sm text-charcoal/50">Approval is required before logging a diagnosis.</p>
                  <CtaButton type="button" onClick={requestAccess} disabled={selected.access_status === "pending"}>
                    {selected.access_status === "pending" ? "Waiting for approval" : "Request access"}
                  </CtaButton>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-charcoal/45">Select a patient.</p>
          )}
          {info ? <p className="mt-4 text-sm text-mint">{info}</p> : null}
          {error ? <p className="mt-4 text-sm text-severity-high">{error}</p> : null}
        </Card>
      </div>

      {activeFlag ? (
        <div className="fixed inset-0 z-40 flex justify-end bg-charcoal/25">
          <button type="button" className="h-full flex-1 cursor-default" aria-label="Close" onClick={() => setActiveFlag(null)} />
          <aside className="h-full w-full max-w-md overflow-y-auto bg-offwhite p-6 shadow-[0_16px_40px_rgba(43,45,47,0.16)]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">{activeFlag.patient_name}</h2>
                <p className="mt-1 text-sm text-charcoal/50">{activeFlag.root_cause}</p>
              </div>
              <SeverityBadge severity={activeFlag.severity || "high"} />
            </div>
            <div className="mt-6 space-y-4 text-sm leading-relaxed">
              <p>
                <span className="text-charcoal/45">Status</span>
                <span className="ml-2">
                  <StatusPill status={activeFlag.status} />
                </span>
              </p>
              <div>
                <div className="text-charcoal/45">Finding A</div>
                <p className="mt-1 font-medium">{activeFlag.diagnosis_1?.diagnosis_label}</p>
                <p className="text-charcoal/60">{activeFlag.diagnosis_1?.full_notes}</p>
                <p className="text-xs text-charcoal/40">{formatWhen(activeFlag.diagnosis_1?.timestamp)}</p>
              </div>
              <div>
                <div className="text-charcoal/45">Finding B</div>
                <p className="mt-1 font-medium">{activeFlag.diagnosis_2?.diagnosis_label}</p>
                <p className="text-charcoal/60">{activeFlag.diagnosis_2?.full_notes}</p>
                <p className="text-xs text-charcoal/40">{formatWhen(activeFlag.diagnosis_2?.timestamp)}</p>
              </div>
              {activeFlag.status === "resolved" ? (
                <p>
                  <span className="text-charcoal/45">Resolution</span>
                  <span className="mt-1 block">{activeFlag.resolution_note}</span>
                </p>
              ) : (
                <>
                  <textarea
                    className={`${inputClass} min-h-28`}
                    placeholder="Resolution note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                  <CtaButton type="button" className="w-full" onClick={resolve}>
                    Mark Resolved
                  </CtaButton>
                </>
              )}
              <GhostButton type="button" className="w-full" onClick={() => setActiveFlag(null)}>
                Close
              </GhostButton>
            </div>
          </aside>
        </div>
      ) : null}
    </AppShell>
  );
}
