export const SEVERITY_RANK = { critical: 0, high: 1, medium: 2, low: 3 };

export function formatWhen(value) {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

export function notificationTarget(role, note) {
  const home = role === "doctor" ? "/doctor" : role === "surrogate" ? "/surrogate" : "/patient";
  if (note.type?.startsWith("flag")) {
    return role === "doctor" ? `${home}?flag=${note.related_id}` : `${home}?tab=records`;
  }
  if (note.type?.startsWith("access")) {
    return role === "doctor" ? `${home}?tab=patients` : `${home}?tab=consent`;
  }
  if (note.type === "diagnosis_to_surrogate") return "/surrogate?tab=notified";
  if (note.type === "correction_submitted" || note.type === "correction_outcome") {
    return role === "doctor" ? `${home}` : `${home}?tab=correction`;
  }
  if (
    note.type?.includes("conversation") ||
    note.type === "senior_review_complete" ||
    note.type === "senior_review_assigned"
  ) {
    return role === "doctor" ? `${home}?conversation=${note.related_id}` : `${home}?tab=records`;
  }
  if (note.type === "gap_response") return role === "doctor" ? `${home}?flag=${note.related_id}` : `${home}?tab=records`;
  return `${home}?tab=records`;
}

export function EmptyState({ children }) {
  return (
    <p className="py-16 text-center text-[15px] text-[#8a8b89]">{children}</p>
  );
}

export function SeverityBadge({ severity }) {
  const tone =
    severity === "critical" || severity === "high"
      ? "bg-severity-high/15 text-severity-high"
      : severity === "medium"
        ? "bg-severity-medium/15 text-severity-medium"
        : "bg-severity-low/20 text-charcoal/70";
  return (
    <span className={`inline-flex min-w-[4.5rem] justify-center rounded-[10px] px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${tone}`}>
      {severity}
    </span>
  );
}

export function StatusPill({ status }) {
  const resolved = status === "resolved";
  const review = status === "under_review" || status === "pending_review";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
        resolved
          ? "bg-mint/15 text-mint"
          : review
            ? "bg-charcoal/8 text-charcoal"
            : "bg-[#ecece9] text-charcoal/70"
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function AccessStatus({ status }) {
  if (status === "approved") {
    return (
      <span className="inline-flex rounded-full bg-mint/15 px-2.5 py-1 text-xs font-medium text-mint transition-colors">
        Approved
      </span>
    );
  }
  if (status === "denied") {
    return (
      <span className="inline-flex rounded-full bg-charcoal/10 px-2.5 py-1 text-xs font-medium text-charcoal/70">
        Denied
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-[#e6e6e3] px-2.5 py-1 text-xs font-medium text-charcoal/60">
      {status === "pending" ? "History pending" : "Reports only"}
    </span>
  );
}

export function Field({ label, children }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium text-charcoal">
      {label}
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-[10px] border border-charcoal/15 bg-white px-3 py-2.5 text-[15px] font-normal text-charcoal placeholder:text-charcoal/40";

export function CtaButton({ children, className = "", ...props }) {
  return (
    <button
      className={`rounded-[10px] bg-mint px-4 py-2.5 text-sm font-medium text-offwhite transition hover:bg-[#02b38d] disabled:cursor-not-allowed disabled:opacity-45 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, className = "", ...props }) {
  return (
    <button
      className={`rounded-[10px] border border-charcoal/20 bg-transparent px-4 py-2.5 text-sm font-medium text-charcoal hover:border-charcoal/40 disabled:opacity-45 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = "" }) {
  return (
    <section className={`rounded-xl bg-offwhite p-6 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8 ${className}`}>
      {children}
    </section>
  );
}
