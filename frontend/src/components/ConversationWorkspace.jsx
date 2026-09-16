import { useMemo, useState } from "react";
import { api } from "../api";
import { ReportMedia } from "./CarePanels";
import { Card, CtaButton, Field, GhostButton, formatWhen, inputClass } from "../ui";

const BLOCKS = [
  { id: "morning", label: "Morning" },
  { id: "afternoon", label: "Afternoon" },
  { id: "evening", label: "Evening" },
];

function upcomingDays(count = 5) {
  const days = [];
  const start = new Date();
  for (let i = 0; i < count; i += 1) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    const y = day.getFullYear();
    const m = String(day.getMonth() + 1).padStart(2, "0");
    const d = String(day.getDate()).padStart(2, "0");
    const key = `${y}-${m}-${d}`;
    days.push({
      key,
      label: day.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }),
    });
  }
  return days;
}

export default function ConversationWorkspace({ conversations, doctorId, onReload, activeId, onOpen }) {
  const selected = conversations.find((row) => String(row.id) === String(activeId)) || null;
  if (!conversations.length) {
    return (
      <Card>
        <h2 className="text-lg font-semibold">Doctor conversations</h2>
        <p className="mt-2 text-sm text-charcoal/50">
          When two doctors write different treatments for similar symptoms, Hetu asks them to talk. A senior doctor joins after a time is set.
        </p>
      </Card>
    );
  }
  return (
    <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <Card>
        <h2 className="mb-4 text-lg font-semibold">Doctor conversations</h2>
        <div className="space-y-2">
          {conversations.map((row) => (
            <button
              type="button"
              key={row.id}
              onClick={() => onOpen(row.id)}
              className={`w-full rounded-[10px] px-3 py-3 text-left ${
                selected?.id === row.id ? "bg-white ring-1 ring-mint" : "hover:bg-white/70"
              }`}
            >
              <span className="block font-medium">{row.patient_name}</span>
              <span className="text-xs text-charcoal/50">
                {row.issue_type} · {row.status.replaceAll("_", " ")}
              </span>
            </button>
          ))}
        </div>
      </Card>
      {selected ? (
        <ConversationDetail conversation={selected} doctorId={doctorId} onReload={onReload} />
      ) : (
        <Card>
          <p className="text-sm text-charcoal/50">Select a conversation.</p>
        </Card>
      )}
    </section>
  );
}

function ConversationDetail({ conversation, doctorId, onReload }) {
  const days = useMemo(() => upcomingDays(5), []);
  const [slots, setSlots] = useState([]);
  const [note, setNote] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [agreed, setAgreed] = useState(true);
  const [goodTreatment, setGoodTreatment] = useState(true);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const isSenior = conversation.senior_doctor?.id === doctorId;
  const waitingOnSenior = Boolean(conversation.senior_doctor?.id) && !isSenior && conversation.status !== "completed";
  const needsSchedule = conversation.status === "pending_schedule" && !isSenior;
  const alreadySubmitted = (conversation.availability_submitted || []).includes(doctorId);

  function toggleSlot(slot) {
    setSlots((current) => (current.includes(slot) ? current.filter((item) => item !== slot) : [...current, slot]));
  }

  async function sendAvailability(e) {
    e.preventDefault();
    setError("");
    try {
      await api.submitAvailability(conversation.id, slots);
      setInfo("Availability sent.");
      await onReload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendNote(e) {
    e.preventDefault();
    setError("");
    try {
      await api.addConversationNote(conversation.id, note);
      setNote("");
      await onReload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function complete() {
    setError("");
    try {
      await api.completeConversation(conversation.id, {
        conclusion,
        agreed: isSenior ? true : agreed,
        good_treatment: isSenior ? goodTreatment : true,
      });
      setConclusion("");
      setInfo("Conversation updated.");
      await onReload();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold">{conversation.patient_name}</h2>
      <p className="mt-1 text-sm text-charcoal/55">
        {conversation.issue_type} · {conversation.duration_minutes} minutes
        {conversation.scheduled_time ? ` · ${formatWhen(conversation.scheduled_time)}` : ""}
        {conversation.schedule_deadline && conversation.status === "pending_schedule"
          ? ` · schedule by ${formatWhen(conversation.schedule_deadline)}`
          : ""}
      </p>
      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-charcoal/40">{conversation.status.replaceAll("_", " ")}</p>
      {conversation.senior_doctor ? (
        <p className="mt-2 text-sm text-mint">Reviewing specialist: {conversation.senior_doctor.name}</p>
      ) : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {[conversation.report_1, conversation.report_2].map((report) =>
          report ? (
            <div key={report.id} className="rounded-[10px] bg-white p-3 text-sm ring-1 ring-charcoal/8">
              <p className="font-medium">{report.related_issue}</p>
              <p className="text-charcoal/50">{report.doctor?.name || "Unspecified doctor"}</p>
              {report.notes ? <p className="mt-2 text-sm text-charcoal/70">{report.notes}</p> : null}
              <ReportMedia fileUrl={report.file_url} hasImage={report.has_image} filename={report.original_filename} />
              <p className="mt-2 text-xs text-charcoal/45">
                {formatWhen(report.report_date || report.uploaded_at)}
                {report.original_filename ? ` · ${report.original_filename}` : ""}
              </p>
            </div>
          ) : null
        )}
      </div>
      {needsSchedule ? (
        <form className="mt-6 grid gap-3" onSubmit={sendAvailability}>
          <p className="text-sm font-medium">When could you talk? Pick blocks over the next 5 days.</p>
          {alreadySubmitted ? <p className="text-xs text-charcoal/50">You already submitted times. You can update them.</p> : null}
          {days.map((day) => (
            <div key={day.key} className="flex flex-wrap items-center gap-2">
              <span className="w-28 text-xs text-charcoal/50">{day.label}</span>
              {BLOCKS.map((block) => {
                const slot = `${day.key}:${block.id}`;
                const on = slots.includes(slot);
                return (
                  <button
                    type="button"
                    key={slot}
                    onClick={() => toggleSlot(slot)}
                    className={`rounded-[10px] px-3 py-1.5 text-xs ${on ? "bg-mint text-offwhite" : "bg-white ring-1 ring-charcoal/10"}`}
                  >
                    {block.label}
                  </button>
                );
              })}
            </div>
          ))}
          <CtaButton type="submit" disabled={!slots.length}>
            Submit availability
          </CtaButton>
        </form>
      ) : null}
      <div className="mt-6 space-y-3">
        <h3 className="text-sm font-semibold">Discussion notes</h3>
        {(conversation.notes || []).length === 0 ? (
          <p className="text-sm text-charcoal/45">No notes yet.</p>
        ) : (
          conversation.notes.map((item) => (
            <p key={item.id} className="rounded-[10px] bg-white p-3 text-sm ring-1 ring-charcoal/8">
              <span className="block text-xs text-charcoal/45">
                {item.doctor?.name} · {formatWhen(item.created_at)}
              </span>
              {item.body}
            </p>
          ))
        )}
        {conversation.status !== "completed" && !waitingOnSenior ? (
          <form className="grid gap-3" onSubmit={sendNote}>
            <Field label="Add a note">
              <textarea className={`${inputClass} min-h-20`} value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <GhostButton type="submit" disabled={!note.trim()}>
              Log note
            </GhostButton>
          </form>
        ) : null}
      </div>
      {conversation.status !== "completed" && !waitingOnSenior && conversation.status !== "pending_schedule" ? (
        <div className="mt-6 grid gap-3">
          <Field label={isSenior ? "Final conclusion" : "Summary / conclusion"}>
            <textarea className={`${inputClass} min-h-24`} value={conclusion} onChange={(e) => setConclusion(e.target.value)} />
          </Field>
          {!isSenior ? (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
              We reached a joint conclusion
            </label>
          ) : (
            <p className="text-xs text-charcoal/50">Your conclusion is sent to both doctors and the patient in plain language.</p>
          )}
          {isSenior ? (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={goodTreatment} onChange={(e) => setGoodTreatment(e.target.checked)} />
              This is a sound coordinated treatment (adds credibility)
            </label>
          ) : null}
          <CtaButton type="button" disabled={!conclusion.trim()} onClick={complete}>
            Mark Conversation Complete
          </CtaButton>
        </div>
      ) : null}
      {waitingOnSenior ? (
        <p className="mt-4 text-sm text-charcoal/55">A senior specialist is reviewing this conversation.</p>
      ) : null}
      {conversation.status === "completed" ? (
        <p className="mt-4 rounded-[10px] bg-mint/10 p-3 text-sm">{conversation.conclusion}</p>
      ) : null}
      {info ? <p className="mt-3 text-sm text-mint">{info}</p> : null}
      {error ? <p className="mt-3 text-sm text-severity-high">{error}</p> : null}
    </Card>
  );
}
