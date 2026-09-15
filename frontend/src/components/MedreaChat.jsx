import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import {
  loadMedreaMessages,
  reportAsMessage,
  saveMedreaMessages,
  takeMedreaReport,
} from "../medreaStore";

const ingesting = new Set();

export default function MedreaChat({ userId, compact = false, pageLink = compact }) {
  const [messages, setMessages] = useState(() => loadMedreaMessages(userId));
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  useEffect(() => {
    setMessages(loadMedreaMessages(userId));
  }, [userId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!userId || ingesting.has(userId)) return;
    const report = takeMedreaReport(userId);
    if (!report) return;
    ingesting.add(userId);
    const content = reportAsMessage(report);
    send({ role: "user", content }, report)
      .catch((err) => setError(err.message))
      .finally(() => ingesting.delete(userId));
  }, [userId]);

  async function send(userMsg, report = null) {
    setBusy(true);
    setError("");
    const next = [...loadMedreaMessages(userId), userMsg];
    saveMedreaMessages(userId, next);
    setMessages(next);
    try {
      const { reply } = await api.medreaChat({ messages: next, report });
      const withReply = [...next, { role: "assistant", content: reply }];
      saveMedreaMessages(userId, withReply);
      setMessages(withReply);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    const content = draft.trim();
    if (!content || busy) return;
    setDraft("");
    try {
      await send({ role: "user", content });
    } catch (err) {
      setError(err.message);
    }
  }

  const shown =
    messages.length > 0
      ? messages
      : [
          {
            role: "assistant",
            content:
              "I'm Medrea. Ask how Hetu works, or send a report from your dashboard and choose Medrea.",
          },
        ];

  return (
    <div className={`flex flex-col ${compact ? "h-[min(28rem,70vh)]" : "min-h-[28rem]"}`}>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {shown.map((m, i) => (
          <div
            key={i}
            className={`max-w-[90%] rounded-[10px] px-3 py-2 text-sm leading-relaxed ${
              m.role === "user" ? "ml-auto bg-charcoal text-offwhite" : "bg-white text-charcoal ring-1 ring-charcoal/10"
            }`}
          >
            {m.role !== "user" ? <div className="mb-1 text-xs font-semibold text-mint">Medrea</div> : null}
            {m.content}
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <p className="px-4 text-xs text-charcoal/45">
        Medrea helps you use Hetu; it does not diagnose.
      </p>
      <form className="flex gap-2 p-4" onSubmit={onSubmit}>
        <input
          className="flex-1 rounded-[10px] border border-charcoal/15 bg-white px-3 py-2 text-sm"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask Medrea…"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-[10px] bg-mint px-4 py-2 text-sm font-medium text-offwhite disabled:opacity-45"
        >
          Send
        </button>
      </form>
      {pageLink ? (
        <Link to="/medrea" className="px-4 pb-3 text-center text-sm text-mint">
          Open Medrea page
        </Link>
      ) : null}
      {error ? <p className="px-4 pb-3 text-sm text-severity-high">{error}</p> : null}
    </div>
  );
}
