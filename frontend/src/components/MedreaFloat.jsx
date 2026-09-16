import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import MedreaChat from "./MedreaChat";

export default function MedreaFloat() {
  const { session } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  if (!session?.user || location.pathname === "/medrea") return null;

  return (
    <div className="fixed bottom-8 right-8 z-50">
      {open ? (
        <div className="mb-3 w-[min(22rem,calc(100vw-2.5rem))] overflow-hidden rounded-xl bg-offwhite shadow-[0_16px_40px_rgba(43,45,47,0.14)] ring-1 ring-charcoal/10">
          <div className="flex items-center justify-between bg-charcoal px-4 py-2.5 text-offwhite">
            <span className="text-sm font-bold uppercase tracking-wide">MEDREA</span>
            <button type="button" className="text-offwhite/70" onClick={() => setOpen(false)} aria-label="Close">
              Close
            </button>
          </div>
          <MedreaChat userId={session.user.id} compact />
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-mint text-sm font-semibold text-offwhite shadow-[0_8px_24px_rgba(2,195,154,0.35)]"
        aria-label="Open MEDREA"
      >
        M
      </button>
    </div>
  );
}
