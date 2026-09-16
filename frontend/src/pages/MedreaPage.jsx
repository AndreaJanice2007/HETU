import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import AppShell from "../components/AppShell";
import MedreaChat from "../components/MedreaChat";

function ChatBox({ userId }) {
  return (
    <div className="mx-auto max-w-2xl overflow-hidden rounded-xl bg-white/80 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8 backdrop-blur-[2px]">
      <div className="border-b border-charcoal/8 px-5 py-3">
        <h1 className="text-lg font-bold uppercase tracking-wide">MEDREA</h1>
        <p className="text-xs text-charcoal/50">Help chat — not a diagnosis</p>
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
      <AppShell title="MEDREA" role={session.user.role}>
        <ChatBox userId={userId} />
      </AppShell>
    );
  }

  return (
    <div className="relative z-10 min-h-screen text-charcoal">
      <div className="flex justify-end px-10 pt-20 sm:px-16">
        <Link to="/" className="text-sm font-medium text-mint">
          All roles
        </Link>
      </div>
      <main className="mx-auto w-full max-w-6xl px-8 pb-28 pt-6 sm:px-12">
        <ChatBox userId={userId} />
      </main>
    </div>
  );
}
