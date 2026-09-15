import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { queueMedreaReport } from "../medreaStore";

export default function SendReport({ userId, report }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  function sendToMedrea() {
    queueMedreaReport(userId, report);
    setOpen(false);
    navigate("/medrea");
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-[10px] border border-charcoal/20 px-3 py-2 text-sm font-medium text-charcoal"
      >
        Send report
      </button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 w-52 rounded-xl bg-offwhite p-2 shadow-[0_16px_40px_rgba(43,45,47,0.12)] ring-1 ring-charcoal/10">
          <p className="px-2 py-1 text-xs text-charcoal/50">Send to</p>
          <button
            type="button"
            onClick={sendToMedrea}
            className="w-full rounded-[10px] px-3 py-2 text-left text-sm font-medium text-mint hover:bg-mint/10"
          >
            Medrea
          </button>
        </div>
      ) : null}
    </div>
  );
}
