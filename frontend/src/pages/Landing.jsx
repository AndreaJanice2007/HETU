import { Link, Navigate } from "react-router-dom";
import { roleHome, useAuth } from "../auth";
import BrandMark from "../components/BrandMark";

function Icon({ children }) {
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
      className="text-mint"
      aria-hidden
    >
      {children}
    </svg>
  );
}

function PatientIcon() {
  return (
    <Icon>
      <circle cx="12" cy="8" r="3.2" />
      <path d="M5.5 19.5c.8-3.2 3.3-5 6.5-5s5.7 1.8 6.5 5" />
      <path d="M15.8 8.2c.3-1.4 1.4-2.4 2.7-2.4" />
    </Icon>
  );
}

function DoctorIcon() {
  return (
    <Icon>
      <rect x="3.5" y="7" width="17" height="13.5" rx="2.2" />
      <path d="M12 10.2v7.2M8.4 13.8h7.2" />
      <path d="M8.5 7V5.6A2.1 2.1 0 0 1 10.6 3.5h2.8A2.1 2.1 0 0 1 15.5 5.6V7" />
    </Icon>
  );
}

function MedreaIcon() {
  return (
    <Icon>
      <path d="M4.5 18.5V7.8A2.3 2.3 0 0 1 6.8 5.5h10.4A2.3 2.3 0 0 1 19.5 7.8v6.4a2.3 2.3 0 0 1-2.3 2.3H9.2L4.5 18.5z" />
      <path d="M8.2 9.6h7.6M8.2 12.6h5.2" />
    </Icon>
  );
}

function SurrogateIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="2.6" />
      <circle cx="16" cy="8.5" r="2.2" />
      <path d="M3.8 19c.6-3 2.6-4.6 4.8-4.6 1.4 0 2.6.6 3.5 1.6" />
      <path d="M12.8 18.8c.5-2.2 2-3.5 3.7-3.5 2 0 3.6 1.4 4.2 3.5" />
    </Icon>
  );
}

const ROLES = [
  {
    id: "patient",
    title: "Patient",
    copy: "View your record, explanations, and consent requests.",
    icon: <PatientIcon />,
  },
  {
    id: "doctor",
    title: "Doctor",
    copy: "Log diagnoses, review flags, and close gaps with a note.",
    icon: <DoctorIcon />,
  },
  {
    id: "surrogate",
    title: "Surrogate",
    copy: "Act for a linked patient, including notified diagnoses.",
    icon: <SurrogateIcon />,
  },
];

export default function Landing() {
  const { session } = useAuth();
  if (session?.user) return <Navigate to={roleHome(session.user.role)} replace />;

  return (
    <div className="flex min-h-[calc(100vh-28px)] flex-col items-center bg-offwhite px-5 py-16 text-charcoal">
      <h1>
        <BrandMark size="lg" />
      </h1>
      <p
        className="mt-5 max-w-xl text-center text-xl leading-snug text-charcoal/70 sm:text-2xl"
        style={{ fontFamily: '"Instrument Serif", Georgia, serif' }}
      >
        Find the gap. Understand the why. Improve the care.
      </p>
      <div className="mt-14 grid w-full max-w-4xl gap-5 md:grid-cols-3">
        {ROLES.map((role) => (
          <Link
            key={role.id}
            to={`/login?role=${role.id}`}
            className="rounded-xl border border-charcoal/15 bg-offwhite p-8 text-left shadow-[0_8px_24px_rgba(43,45,47,0.05)] transition hover:border-mint hover:shadow-[0_8px_24px_rgba(2,195,154,0.12)]"
          >
            <h2 className="flex items-center gap-2 text-xl font-semibold uppercase tracking-wide">
              {role.icon}
              {role.title}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-charcoal/60">{role.copy}</p>
          </Link>
        ))}
        <Link
          to="/medrea"
          className="flex flex-col items-start justify-between gap-4 rounded-xl border border-charcoal/15 bg-offwhite px-6 py-5 text-left shadow-[0_8px_24px_rgba(43,45,47,0.05)] transition hover:border-mint hover:shadow-[0_8px_24px_rgba(2,195,154,0.12)] sm:flex-row sm:items-center md:col-span-3"
        >
          <div className="flex items-center gap-3">
            <MedreaIcon />
            <p className="text-sm leading-relaxed text-charcoal/60">
              Ask how Hetu works. Medrea does not diagnose.
            </p>
          </div>
          <span className="rounded-[10px] bg-mint px-4 py-2.5 text-sm font-medium text-offwhite">
            Chat with Medrea
          </span>
        </Link>
      </div>
    </div>
  );
}
