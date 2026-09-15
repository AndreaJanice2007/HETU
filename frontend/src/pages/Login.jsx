import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { roleHome, useAuth } from "../auth";
import BrandMark from "../components/BrandMark";
import { CtaButton, Field, inputClass } from "../ui";

const ROLE_HINT = {
  patient: { label: "Patient", email: "priya.nair@hetu.demo" },
  doctor: { label: "Doctor", email: "arjun.patel@hetu.demo" },
  surrogate: { label: "Surrogate", email: "farah.khan@hetu.demo" },
};

export default function Login() {
  const { session, applySession } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const role = params.get("role");
  const hint = ROLE_HINT[role];
  const [email, setEmail] = useState(hint?.email || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const title = useMemo(() => hint?.label || "Account", [hint]);

  useEffect(() => {
    setEmail(hint?.email || "");
    setPassword("");
    setError("");
  }, [role]);

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
      const payload = await api.login(email, password);
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

  return (
    <div className="flex min-h-[calc(100vh-28px)] items-center justify-center bg-offwhite px-5 py-16">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-xl bg-offwhite p-8 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/10"
      >
        <Link to="/" className="text-sm text-mint">
          All roles
        </Link>
        <h1 className="mt-4">
          <BrandMark />
        </h1>
        <p className="mt-2 text-sm text-charcoal/55">Sign in with a seeded demo account.</p>
        <div className="mt-8 grid gap-5">
          <Field label="Email">
            <input
              className={inputClass}
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </Field>
          <Field label="Password">
            <input
              className={inputClass}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          {error ? <p className="text-sm text-severity-high">{error}</p> : null}
          <CtaButton type="submit" disabled={busy} className="w-full">
            {busy ? "Checking…" : `Continue as ${title}`}
          </CtaButton>
        </div>
      </form>
    </div>
  );
}
