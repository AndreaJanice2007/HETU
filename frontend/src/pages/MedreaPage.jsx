import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import AppShell from "../components/AppShell";
import BrandMark from "../components/BrandMark";
import MedreaChat from "../components/MedreaChat";

function ChatBox({ userId }) {
  return (
    <div className="mx-auto max-w-2xl overflow-hidden rounded-xl bg-offwhite shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
      <div className="bg-charcoal px-5 py-3 text-offwhite">
        <h1 className="text-lg font-semibold">Medrea</h1>
        <p className="text-xs text-offwhite/60">Help chat — not a diagnosis</p>
      </div>
      <MedreaChat userId={userId} />
    </div>
  );
}

export default function MedreaPage() {
  const { session } = useAuth();
  const userId = session?.user?.id ?? "guest";

  if (session?.user) {
    return (
      <AppShell title="Medrea" role={session.user.role}>
        <ChatBox userId={userId} />
      </AppShell>
    );
  }

  return (
    <div className="min-h-[calc(100vh-28px)] bg-offwhite text-charcoal">
      <header className="sticky top-[14px] z-30 flex items-center justify-between bg-charcoal px-5 py-3 text-offwhite">
        <Link to="/" aria-label="Back to home">
          <BrandMark />
        </Link>
        <Link to="/" className="text-sm text-mint">
          All roles
        </Link>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-10">
        <ChatBox userId={userId} />
      </main>
    </div>
  );
}
