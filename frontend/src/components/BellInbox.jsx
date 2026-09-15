import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { formatWhen, notificationTarget } from "../ui";

export default function BellInbox({ role, onOpen }) {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const box = useRef(null);
  const unread = items.filter((n) => !n.read).length;

  async function load() {
    if (!session?.user) return;
    setItems(await api.notifications());
  }

  useEffect(() => {
    load().catch(() => {});
  }, [session?.user?.id]);

  useEffect(() => {
    function onDoc(e) {
      if (box.current && !box.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  async function openNote(note) {
    if (!note.read) {
      await api.readNotification(note.id);
      await load();
    }
    setOpen(false);
    const to = notificationTarget(role, note);
    onOpen?.(note);
    navigate(to);
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        className="relative grid h-10 w-10 place-items-center rounded-[10px] text-offwhite hover:bg-white/10"
        onClick={() => {
          setOpen((v) => !v);
          load().catch(() => {});
        }}
        aria-label="Notifications"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M6 9a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9Z"
            stroke="currentColor"
            strokeWidth="1.7"
          />
          <path d="M10 20a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.7" />
        </svg>
        {unread > 0 ? (
          <span className="absolute right-1.5 top-1.5 h-2.5 w-2.5 rounded-full bg-mint" />
        ) : null}
      </button>
      {open ? (
        <div className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl bg-offwhite shadow-[0_16px_40px_rgba(43,45,47,0.12)] ring-1 ring-charcoal/10">
          <div className="border-b border-charcoal/8 px-4 py-3 text-sm font-semibold">Inbox</div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-charcoal/50">No notifications.</p>
            ) : (
              items.map((n) => (
                <button
                  type="button"
                  key={n.id}
                  onClick={() => openNote(n)}
                  className={`block w-full border-b border-charcoal/6 px-4 py-3 text-left text-sm last:border-0 ${
                    n.read ? "text-charcoal/50" : "font-semibold text-charcoal"
                  }`}
                >
                  <span className="flex items-start gap-2">
                    {!n.read ? <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-mint" /> : <span className="w-1.5" />}
                    <span>
                      {n.message}
                      <span className="mt-1 block text-xs font-normal text-charcoal/40">{formatWhen(n.timestamp)}</span>
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
