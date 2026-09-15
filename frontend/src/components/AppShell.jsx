import { useState } from "react";
import { useAuth } from "../auth";
import BellInbox from "./BellInbox";
import BrandMark from "./BrandMark";
import MedreaFloat from "./MedreaFloat";

export default function AppShell({ title, role, children }) {
  const { session, logout } = useAuth();
  const [menu, setMenu] = useState(false);
  const user = session?.user;

  return (
    <div className="min-h-[calc(100vh-28px)] bg-offwhite text-charcoal">
      <header className="sticky top-[14px] z-30 flex items-center justify-between bg-charcoal px-5 py-3 text-offwhite">
        <div className="flex items-center gap-3">
          <BrandMark />
          <span className="hidden text-xs text-offwhite/55 sm:inline">{title}</span>
        </div>
        <div className="flex items-center gap-1">
          <BellInbox role={role} />
          <div className="relative">
            <button
              type="button"
              className="grid h-10 w-10 place-items-center rounded-full bg-white/10 text-sm font-semibold"
              onClick={() => setMenu((v) => !v)}
              aria-label="Profile"
            >
              {(user?.name || "?").split(" ").map((p) => p[0]).slice(0, 2).join("")}
            </button>
            {menu ? (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-offwhite p-3 text-charcoal shadow-[0_16px_40px_rgba(43,45,47,0.12)] ring-1 ring-charcoal/10">
                <div className="text-sm font-semibold">{user?.name}</div>
                <div className="mt-0.5 text-xs capitalize text-charcoal/50">{user?.role}</div>
                <button
                  type="button"
                  className="mt-3 w-full rounded-[10px] bg-charcoal px-3 py-2 text-sm text-offwhite"
                  onClick={logout}
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-10">{children}</main>
      <MedreaFloat />
    </div>
  );
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <nav className="mb-8 flex flex-wrap gap-1 border-b border-charcoal/10">
      {tabs.map((tab) => (
        <button
          type="button"
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`-mb-px rounded-t-[10px] px-4 py-2.5 text-sm font-medium ${
            active === tab.id
              ? "border-b-2 border-mint text-mint"
              : "text-charcoal/55 hover:text-charcoal"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
