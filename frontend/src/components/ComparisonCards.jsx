import { formatWhen } from "../ui";

export default function ComparisonCards({ diagnosisA, diagnosisB, className = "" }) {
  return (
    <div className={`grid gap-4 md:grid-cols-2 ${className}`}>
      <FindingCard title="Finding A" diagnosis={diagnosisA} />
      <FindingCard title="Finding B" diagnosis={diagnosisB} />
    </div>
  );
}

function FindingCard({ title, diagnosis }) {
  const doctorName = diagnosis?.doctor?.name;
  return (
    <article className="rounded-[10px] bg-offwhite p-5 text-sm leading-relaxed text-charcoal shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-charcoal/45">{title}</p>
      {doctorName ? <p className="mt-2 text-xs text-charcoal/50">{doctorName}</p> : null}
      <p className="mt-1 text-base font-semibold">{diagnosis?.diagnosis_label || "—"}</p>
      {diagnosis?.full_notes ? <p className="mt-2 text-charcoal/60">{diagnosis.full_notes}</p> : null}
      <p className="mt-3 text-xs text-charcoal/40">{formatWhen(diagnosis?.timestamp)}</p>
    </article>
  );
}
