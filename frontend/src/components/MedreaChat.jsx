import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import MedreaReply from "./MedreaReply";
import {
  loadMedreaMessages,
  reportAsMessage,
  saveMedreaMessages,
  takeMedreaReport,
} from "../medreaStore";

const ingesting = new Set();
const ACCEPT = ".pdf,.docx,.jpg,.jpeg,.png";
const MAX_BYTES = 12 * 1024 * 1024;

function listLines(title, items) {
  if (!items?.length) return "";
  return `${title}:\n${items.map((item) => `- ${item}`).join("\n")}`;
}

function formatClinicalExtract(filename, clinical, processing) {
  const patient = clinical?.patient || {};
  const meta = clinical?.document_metadata || {};
  const parts = [
    `Filename: ${filename}`,
    processing?.detected_type ? `Detected type: ${processing.detected_type}` : "",
    meta.document_type ? `Document type: ${meta.document_type}` : "",
    meta.date ? `Date: ${meta.date}` : "",
    [patient.name, patient.age, patient.sex].filter(Boolean).length
      ? `Patient on document: ${[patient.name, patient.age && `age ${patient.age}`, patient.sex]
          .filter(Boolean)
          .join(", ")}`
      : "",
    listLines("Diagnoses", clinical?.diagnoses),
    listLines("Medications", clinical?.medications),
    listLines("Lab results", clinical?.lab_results),
    listLines("Symptoms", clinical?.symptoms),
    listLines("Clinical findings", clinical?.clinical_findings),
    listLines("Procedures", clinical?.procedures),
    listLines("Doctor notes", clinical?.doctor_notes),
    listLines("Uncertainties", clinical?.uncertainties),
  ];
  return parts.filter(Boolean).join("\n");
}

export default function MedreaChat({ userId, compact = false, pageLink = compact }) {
  const [messages, setMessages] = useState(() => loadMedreaMessages(userId));
  const [draft, setDraft] = useState("");
  const [attached, setAttached] = useState(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const bottom = useRef(null);
  const fileInput = useRef(null);

  useEffect(() => {
    setMessages(loadMedreaMessages(userId));
  }, [userId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  useEffect(() => {
    if (!userId || ingesting.has(userId)) return;
    const report = takeMedreaReport(userId);
    if (!report) return;
    ingesting.add(userId);
    const content = reportAsMessage(report);
    send({ role: "user", content }, { report })
      .catch((err) => setError(err.message))
      .finally(() => ingesting.delete(userId));
  }, [userId]);

  async function send(userMsg, { report = null, apiContent = null } = {}) {
    setBusy(true);
    setError("");
    const next = [...loadMedreaMessages(userId), userMsg];
    saveMedreaMessages(userId, next);
    setMessages(next);
    try {
      const forApi = apiContent ? [...next.slice(0, -1), { role: "user", content: apiContent }] : next;
      const { reply } = await api.medreaChat({ messages: forApi, report });
      const withReply = [...next, { role: "assistant", content: reply }];
      saveMedreaMessages(userId, withReply);
      setMessages(withReply);
    } finally {
      setBusy(false);
      setStatus("");
    }
  }

  async function sendWithFile(file, question) {
    const visible = question
      ? `Uploaded document: ${file.name}\n${question}`
      : `Uploaded document: ${file.name}`;
    const userMsg = { role: "user", content: visible };
    const next = [...loadMedreaMessages(userId), userMsg];
    saveMedreaMessages(userId, next);
    setMessages(next);
    setBusy(true);
    setError("");
    setStatus(`Reading ${file.name}…`);
    try {
      const extracted = await api.extractDocument(file);
      const summary = formatClinicalExtract(file.name, extracted.clinical, extracted.processing);
      setStatus("Asking MEDREA…");
      const questionBit = question ? `The user also asked: ${question}\n\n` : "";
      const apiContent =
        `I uploaded ${file.name}. ${questionBit}` +
        `Here is the extracted clinical summary. Explain it in plain language. ` +
        `Answer the user's question if they asked one. Do not diagnose me or say that I have this condition.\n\n${summary}`;
      const { reply } = await api.medreaChat({
        messages: [...next.slice(0, -1), { role: "user", content: apiContent }],
      });
      const withReply = [...next, { role: "assistant", content: reply }];
      saveMedreaMessages(userId, withReply);
      setMessages(withReply);
    } catch (err) {
      setError(typeof err.message === "string" ? err.message : "Could not read that document.");
    } finally {
      setBusy(false);
      setStatus("");
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const content = draft.trim();
    const file = attached;
    if (!content && !file) return;
    setDraft("");
    setAttached(null);
    if (fileInput.current) fileInput.current.value = "";
    try {
      if (file) {
        await sendWithFile(file, content);
      } else {
        await send({ role: "user", content });
      }
    } catch (err) {
      setError(err.message);
    }
  }

  function onFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError("File is larger than 12 MB.");
      return;
    }
    if (!/\.(pdf|docx|jpe?g|png)$/i.test(file.name)) {
      setError("Upload a PDF, DOCX, JPG, or PNG.");
      return;
    }
    setError("");
    setAttached(file);
  }

  function clearAttached() {
    setAttached(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  const shown =
    messages.length > 0
      ? messages
      : [
          {
            role: "assistant",
            content:
              "I'm MEDREA. Ask how Hetu works, ask me to explain a medical term, or attach a PDF, DOCX, JPG, or PNG and press Send. I do not diagnose.",
          },
        ];

  return (
    <div className={`flex flex-col ${compact ? "h-[min(28rem,70vh)]" : "min-h-[28rem]"}`}>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {shown.map((m, i) => (
          <div
            key={i}
            className={`rounded-[10px] px-3.5 py-3 text-sm leading-relaxed ${
              m.role === "user"
                ? "ml-auto max-w-[90%] bg-charcoal text-offwhite"
                : "mr-auto w-full max-w-[95%] bg-white text-charcoal ring-1 ring-charcoal/10"
            }`}
          >
            {m.role !== "user" ? <div className="mb-1 text-xs font-bold uppercase tracking-wide text-mint">MEDREA</div> : null}
            {m.role === "user" ? (
              <div className="whitespace-pre-wrap">{m.content}</div>
            ) : (
              <MedreaReply text={m.content} />
            )}
          </div>
        ))}
        {status ? <p className="text-xs text-charcoal/50">{status}</p> : null}
        <div ref={bottom} />
      </div>
      <p className="px-4 text-xs text-charcoal/45">
        <span className="font-bold">MEDREA</span> helps you use Hetu; it does not diagnose. Use fictional demo files only.
      </p>
      <form className="flex flex-col gap-2 p-4" onSubmit={onSubmit}>
        <input ref={fileInput} type="file" accept={ACCEPT} className="hidden" onChange={onFile} />
        {attached ? (
          <div className="flex items-center justify-between gap-2 rounded-[10px] bg-white px-3 py-2 text-sm ring-1 ring-charcoal/10">
            <span className="truncate text-charcoal">{attached.name}</span>
            <button type="button" className="shrink-0 text-xs text-charcoal/50" onClick={clearAttached}>
              Remove
            </button>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[8rem] flex-1 rounded-[10px] border border-charcoal/15 bg-white px-3 py-2 text-sm"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={attached ? "Add a question about this file, then press Send" : "Ask MEDREA…"}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
            className="rounded-[10px] border border-charcoal/15 bg-white px-4 py-2 text-sm font-medium text-charcoal disabled:opacity-45"
          >
            Upload
          </button>
          <button
            type="submit"
            disabled={busy || (!draft.trim() && !attached)}
            className="rounded-[10px] bg-mint px-4 py-2 text-sm font-medium text-offwhite disabled:opacity-45"
          >
            Send
          </button>
        </div>
      </form>
      {pageLink ? (
        <Link to="/medrea" className="px-4 pb-3 text-center text-sm font-bold uppercase tracking-wide text-mint">
          Open MEDREA page
        </Link>
      ) : null}
      {error ? <p className="px-4 pb-3 text-sm text-severity-high">{error}</p> : null}
    </div>
  );
}
