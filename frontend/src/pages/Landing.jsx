import { Link, Navigate } from "react-router-dom";
import { roleHome, useAuth } from "../auth";
import BrandMark from "../components/BrandMark";

function StrokeIcon({ children, className = "" }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  );
}

function PatientIcon() {
  return (
    <StrokeIcon>
      <circle cx="12" cy="8" r="3.2" />
      <path d="M5.5 19.5c.8-3.2 3.3-5 6.5-5s5.7 1.8 6.5 5" />
      <path d="M15.8 8.2c.3-1.4 1.4-2.4 2.7-2.4" />
    </StrokeIcon>
  );
}

function DoctorIcon() {
  return (
    <StrokeIcon>
      <rect x="3.5" y="7" width="17" height="13.5" rx="2.2" />
      <path d="M12 10.2v7.2M8.4 13.8h7.2" />
      <path d="M8.5 7V5.6A2.1 2.1 0 0 1 10.6 3.5h2.8A2.1 2.1 0 0 1 15.5 5.6V7" />
    </StrokeIcon>
  );
}

function SurrogateIcon() {
  return (
    <StrokeIcon>
      <circle cx="8" cy="8" r="2.6" />
      <circle cx="16" cy="8.5" r="2.2" />
      <path d="M3.8 19c.6-3 2.6-4.6 4.8-4.6 1.4 0 2.6.6 3.5 1.6" />
      <path d="M12.8 18.8c.5-2.2 2-3.5 3.7-3.5 2 0 3.6 1.4 4.2 3.5" />
    </StrokeIcon>
  );
}

function MedreaIcon() {
  return (
    <StrokeIcon>
      <path d="M4.5 18.5V7.8A2.3 2.3 0 0 1 6.8 5.5h10.4A2.3 2.3 0 0 1 19.5 7.8v6.4a2.3 2.3 0 0 1-2.3 2.3H9.2L4.5 18.5z" />
      <path d="M8.2 9.6h7.6M8.2 12.6h5.2" />
    </StrokeIcon>
  );
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Wave({ className, style }) {
  return (
    <svg viewBox="0 0 280 24" className={className} style={style} preserveAspectRatio="none" aria-hidden>
      <path
        d="M0 16 C48 16 62 7 108 9 C158 11 176 20 232 13 C258 10 272 8 280 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PersonMark() {
  return (
    <svg viewBox="0 0 80 100" className="h-full w-full" fill="currentColor" aria-hidden>
      <circle cx="40" cy="18" r="10" />
      <path d="M16 96c2-26 12-40 24-40s22 14 24 40Z" />
    </svg>
  );
}

function StethoscopeMark() {
  return (
    <svg viewBox="0 0 90 90" className="h-full w-full" fill="none" stroke="currentColor" strokeWidth="3.2" aria-hidden>
      <path d="M28 18v22a17 17 0 0 0 34 0V18" />
      <path d="M28 18h6M62 18h6" />
      <path d="M62 57c10 4 16 14 16 24" />
      <circle cx="78" cy="84" r="5" />
    </svg>
  );
}

function PeopleMark() {
  return (
    <svg viewBox="0 0 90 90" className="h-full w-full" fill="currentColor" aria-hidden>
      <circle cx="34" cy="24" r="10" opacity="0.7" />
      <path d="M12 82c2-18 10-28 22-28s20 10 22 28Z" opacity="0.7" />
      <circle cx="62" cy="22" r="9" />
      <path d="M42 82c2-16 10-26 20-26s18 10 20 26Z" />
    </svg>
  );
}

function BubblesMark() {
  return (
    <svg viewBox="0 0 140 90" className="h-full w-full" fill="currentColor" aria-hidden>
      <rect x="8" y="18" width="72" height="48" rx="16" opacity="0.55" />
      <circle cx="32" cy="42" r="4" opacity="0.9" />
      <circle cx="44" cy="42" r="4" opacity="0.9" />
      <circle cx="56" cy="42" r="4" opacity="0.9" />
      <rect x="62" y="8" width="58" height="40" rx="14" opacity="0.35" />
      <path d="M118 6l4 8 8-3-5 8 8 4-9 2 2 8-8-5-6 7 1-9-9-1 8-5Z" opacity="0.45" />
    </svg>
  );
}

const ROLES = [
  {
    id: "patient",
    title: "Patient",
    copy: "View your record, explanations, and consent requests.",
    tag: "Your health, your story",
    color: "#02c39a",
    soft: "rgba(2,195,154,0.14)",
    icon: <PatientIcon />,
    mark: <PersonMark />,
  },
  {
    id: "doctor",
    title: "Doctor",
    copy: "Log diagnoses, review flags, and close gaps with a note.",
    tag: "Better insights. Better care.",
    color: "#4c8ddb",
    soft: "rgba(76,141,219,0.14)",
    icon: <DoctorIcon />,
    mark: <StethoscopeMark />,
  },
  {
    id: "surrogate",
    title: "Surrogate",
    copy: "Act for a linked patient, including notified diagnoses.",
    tag: "Supporting what matters",
    color: "#7b74e8",
    soft: "rgba(123,116,232,0.14)",
    icon: <SurrogateIcon />,
    mark: <PeopleMark />,
  },
];

function RoleCard({ role }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl bg-white/90 p-6 text-left shadow-[0_10px_28px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
      <div
        className="pointer-events-none absolute -bottom-3 -right-2 h-32 w-28 opacity-[0.16]"
        style={{ color: role.color }}
      >
        {role.mark}
      </div>
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: role.soft, color: role.color }}
          >
            {role.icon}
          </span>
          <h2 className="text-lg font-semibold uppercase tracking-wide">{role.title}</h2>
        </div>
      </div>
      <p className="relative mt-3 max-w-[15.5rem] text-sm leading-relaxed text-charcoal/55">{role.copy}</p>
      <div className="relative mt-5 flex flex-wrap gap-2">
        <Link
          to={`/login?role=${role.id}`}
          className="rounded-full px-4 py-2 text-sm font-medium text-white"
          style={{ background: role.color }}
        >
          Sign in
        </Link>
        <Link
          to={`/signup?role=${role.id}`}
          className="rounded-full px-4 py-2 text-sm font-medium ring-1 ring-charcoal/15"
          style={{ color: role.color }}
        >
          Sign up
        </Link>
      </div>
      <Wave className="relative mt-8 h-5 w-[70%]" style={{ color: role.color }} />
      <p
        className="relative mt-2 text-[10px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: role.color }}
      >
        {role.tag}
      </p>
    </div>
  );
}

export default function Landing() {
  const { session } = useAuth();
  if (session?.user) return <Navigate to={roleHome(session.user.role)} replace />;

  return (
    <div className="relative z-10 flex min-h-screen flex-col items-center px-8 pb-28 pt-20 text-charcoal sm:px-12">
      <BrandMark size="lg" className="mb-6" />
      <p
        className="max-w-xl text-center text-xl leading-snug text-charcoal/70 sm:text-2xl"
        style={{ fontFamily: '"Instrument Serif", Georgia, serif' }}
      >
        Find the gap. Understand the why. Improve the care.
      </p>
      <div className="mt-14 grid w-full max-w-5xl gap-5 md:grid-cols-3">
        {ROLES.map((role) => (
          <RoleCard key={role.id} role={role} />
        ))}
        <Link
          to="/rank"
          className="flex items-center justify-between gap-4 rounded-2xl bg-white/90 px-6 py-4 text-left shadow-[0_10px_28px_rgba(43,45,47,0.06)] ring-1 ring-mint/40 transition hover:-translate-y-0.5 md:col-span-3"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mint">Public</p>
            <h2 className="mt-1 text-lg font-semibold uppercase tracking-wide">Best doctor rank</h2>
            <p className="mt-0.5 text-sm text-charcoal/55">Credibility board after senior-reviewed conversations.</p>
          </div>
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mint/15 text-mint">
            <ArrowIcon />
          </span>
        </Link>
        <Link
          to="/medrea"
          className="group relative overflow-hidden rounded-2xl bg-white/90 p-6 text-left shadow-[0_10px_28px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8 transition hover:-translate-y-0.5 hover:shadow-[0_14px_32px_rgba(43,45,47,0.1)] md:col-span-3"
        >
          <div className="pointer-events-none absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-[#f8e4c8]/70 to-transparent" />
          <div className="pointer-events-none absolute -right-2 bottom-2 h-28 w-44 text-[#e89a4a] opacity-40">
            <BubblesMark />
          </div>
          <div className="relative flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e89a4a]/15 text-[#e89a4a]">
                <MedreaIcon />
              </span>
              <div>
                <h2 className="text-lg font-semibold uppercase tracking-wide">Medrea</h2>
                <p className="mt-1 text-sm leading-relaxed text-charcoal/55">
                  Ask how Hetu works.{" "}
                  <em className="italic text-charcoal">It does not diagnose.</em>
                </p>
              </div>
            </div>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#e89a4a]/15 text-[#e89a4a]">
              <ArrowIcon />
            </span>
          </div>
          <Wave className="relative mt-8 h-5 w-[58%] text-[#e89a4a]" />
          <p className="relative mt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#e89a4a]">
            Clear answers. A more connected you.
          </p>
        </Link>
      </div>
    </div>
  );
}
