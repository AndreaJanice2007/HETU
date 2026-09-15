import { formatWhen, EmptyState } from "../ui";

export function RecordsTimeline({ diagnoses, empty = "No records yet." }) {
  if (!diagnoses.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ol className="relative ml-2 space-y-5 border-l border-charcoal/10 pl-6">
      {diagnoses.map((dx) => (
        <li key={dx.id} className="relative">
          <span className="absolute -left-[31px] top-4 h-2.5 w-2.5 rounded-full bg-charcoal/25" />
          <article className="rounded-xl bg-offwhite p-5 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-base font-semibold">{dx.diagnosis_label || "On file"}</h3>
              <span className="text-xs text-charcoal/45">{formatWhen(dx.timestamp)}</span>
            </div>
            <p className="mt-1 text-sm text-charcoal/55">
              {dx.doctor?.name}
              {dx.doctor?.specialty ? ` · ${dx.doctor.specialty}` : ""}
            </p>
            {dx.full_notes ? <p className="mt-3 text-sm leading-relaxed">{dx.full_notes}</p> : null}
          </article>
        </li>
      ))}
    </ol>
  );
}

export function ExplainerView({ explainer }) {
  if (!explainer) return <EmptyState>Loading explanation…</EmptyState>;
  const notes = explainer.original_notes || [];
  const plain = [explainer.audience, explainer.flags, explainer.diagnoses].filter(Boolean).join(" ");

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div>
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-charcoal/40">Clinical notes</p>
        {notes.length === 0 ? (
          <p className="text-sm text-charcoal/40">No disclosed clinical notes on this record.</p>
        ) : (
          <div className="space-y-4">
            {notes.map((note, i) => (
              <div key={i} className="text-sm leading-relaxed text-charcoal/45">
                <div className="text-xs">
                  {note.doctor} · {note.label}
                </div>
                <p className="mt-1">{note.full_notes || "No narrative notes."}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <span className="mb-3 inline-flex rounded-full bg-mint/15 px-2.5 py-1 text-xs font-medium text-mint">
          Simplified by AI
        </span>
        <p className="text-base leading-7 text-charcoal">{plain}</p>
        <p className="mt-4 text-sm text-charcoal/50">{explainer.disclaimer}</p>
      </div>
    </div>
  );
}

export function ConsentCenter({ access, canWrite, onDecide }) {
  if (!access.length) {
    return <EmptyState>No access requests yet.</EmptyState>;
  }
  return (
    <div className="space-y-4">
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
