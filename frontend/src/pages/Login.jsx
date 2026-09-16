import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { roleHome, useAuth } from "../auth";
import BrandMark from "../components/BrandMark";
import DoctorLoginHero, { DoctorLoginFigure } from "../components/DoctorLoginHero";
import PatientLoginHero, { PatientLoginFigure } from "../components/PatientLoginHero";
import SurrogateLoginHero, { SurrogateLoginFigure } from "../components/SurrogateLoginHero";
import { Field, inputClass } from "../ui";

const ROLE_HINT = {
  patient: { label: "Patient" },
  doctor: { label: "Doctor" },
  surrogate: { label: "Surrogate" },
};

function BackButton({ onClick, className = "text-mint" }) {
  return (
    <button type="button" onClick={onClick} className={`inline-flex items-center gap-1.5 text-sm ${className}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path d="M15 6 9 12l6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Back
    </button>
  );
}

function MailIcon() {
  return (
    <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal/35" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3.5" y="6" width="17" height="12" rx="2" stroke="currentColor" strokeWidth="1.7" />
      <path d="M4 7.5 12 13l8-5.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal/35" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="1.7" />
      <path d="M8 11V8.5A4 4 0 0 1 16 8.5V11" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

export default function Login() {
  const { session, applySession } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const role = params.get("role");
  const hint = ROLE_HINT[role];
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setIdentifier("");
    setPassword("");
    setShowPassword(false);
    setError("");
  }, [role, hint]);

  if (session?.user) {
    return <Navigate to={roleHome(session.user.role)} replace />;
  }
  if (!hint) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await api.login(identifier, password);
      if (payload.user.role !== role) {
        setError(`This account is a ${payload.user.role}, not a ${role}.`);
        return;
      }
      applySession(payload);
      navigate(roleHome(payload.user.role));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const formCopy = {
    patient: {
      title: "Welcome Back",
      subtitle: "Sign in to access your health account.",
      idLabel: "Username or email",
      passwordLabel: "Password",
      passwordPlaceholder: "Enter your password",
    },
    doctor: {
      title: "Doctor sign in",
      subtitle: "Access your account to manage patient care.",
      idLabel: "Username or email",
      passwordLabel: "Password",
      passwordPlaceholder: "Enter your password",
    },
    surrogate: {
      title: "Surrogate sign in",
      subtitle: "Sign in with your username or email and password.",
      idLabel: "Username or email",
      passwordLabel: "Password",
      passwordPlaceholder: "Enter your password",
    },
  }[role];

  return (
    <div className="relative z-10 h-dvh overflow-y-auto">
    <div className="mx-auto grid min-h-full max-w-6xl items-start px-8 py-6 max-lg:pb-16 lg:grid-cols-[minmax(22rem,1.3fr)_minmax(13rem,16rem)_minmax(22rem,25rem)] lg:gap-6 lg:px-12">
      <div className="justify-self-start text-left">
        <div className="mb-4 h-12">
          <div className="origin-left scale-[0.44]">
            <BrandMark size="lg" />
          </div>
        </div>
        {role === "doctor" ? <DoctorLoginHero /> : role === "surrogate" ? <SurrogateLoginHero /> : <PatientLoginHero />}
      </div>
      {role === "doctor" ? <DoctorLoginFigure /> : role === "surrogate" ? <SurrogateLoginFigure /> : <PatientLoginFigure />}
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md justify-self-center rounded-2xl bg-white p-6 shadow-[0_12px_32px_rgba(43,45,47,0.08)] ring-1 ring-charcoal/8 sm:p-7"
      >
        <BackButton onClick={() => navigate("/")} className="text-mint" />
        <h1 className="mt-3 text-2xl font-bold tracking-tight">{formCopy.title}</h1>
        <p className="mt-1.5 text-sm text-charcoal/55">{formCopy.subtitle}</p>
        <div className="mt-5 grid gap-4">
          <Field label={formCopy.idLabel}>
            <span className="relative block">
              <MailIcon />
              <input
                className={`${inputClass} pl-10`}
                type="text"
                autoComplete="username"
                placeholder="Username or email"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
              />
            </span>
          </Field>
          <Field label={formCopy.passwordLabel}>
            <span className="relative block">
              <LockIcon />
              <input
                className={`${inputClass} px-10`}
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder={formCopy.passwordPlaceholder}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-charcoal/40"
                onClick={() => setShowPassword((open) => !open)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M3 12s3.6-6.5 9-6.5S21 12 21 12s-3.6 6.5-9 6.5S3 12 3 12z" stroke="currentColor" strokeWidth="1.7" />
                  <circle cx="12" cy="12" r="2.4" stroke="currentColor" strokeWidth="1.7" />
                </svg>
              </button>
            </span>
          </Field>
          {error ? <p className="text-sm text-severity-high">{error}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="mt-1 flex w-full items-center justify-center gap-2 rounded-full bg-mint py-3 text-sm font-medium text-white transition hover:bg-[#02b38d] disabled:cursor-not-allowed disabled:opacity-45"
          >
            {busy ? "Checking…" : "Sign in"}
            {busy ? null : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
          <p className="text-center text-sm text-charcoal/55">
            New here?{" "}
            <button type="button" className="font-medium text-mint" onClick={() => navigate(`/signup?role=${role}`)}>
              Create an account
            </button>
          </p>
        </div>
      </form>
    </div>
    </div>
  );
}
