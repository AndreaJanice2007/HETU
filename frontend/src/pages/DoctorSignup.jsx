import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { roleHome, useAuth } from "../auth";
import BrandMark from "../components/BrandMark";
import { CtaButton, Field, GhostButton, inputClass } from "../ui";

export default function DoctorSignup() {
  const { applySession } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("prefill_token") || "";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [hospital, setHospital] = useState("Independent practice");
  const [dateOfBirth, setDateOfBirth] = useState("1980-01-15");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Open this page from a guest judgment to create a profile.");
      return;
    }
    api
      .guestJudgePrefill(token)
      .then((data) => {
        setName(data.name || "");
        setEmail(data.email || "");
        setSpecialty(data.specialty || "");
        setLicenseNumber(data.license_number || "");
      })
      .catch((err) => setError(err.message));
  }, [token]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = await api.doctorSignup({
        name,
        email,
        password,
        specialty,
        hospital,
        license_number: licenseNumber,
        date_of_birth: dateOfBirth,
        prefill_token: token,
      });
      applySession(payload);
      navigate(roleHome("doctor"), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative z-10 min-h-screen bg-offwhite px-5 py-12 text-charcoal">
      <div className="mx-auto w-full max-w-md">
        <BrandMark size="md" className="mb-8" />
        <h1 className="text-2xl font-semibold">Create your Hetu profile</h1>
        <p className="mt-2 text-sm text-charcoal/60">
          Your credibility score will start with the guest case you just resolved.
        </p>
        <form className="mt-8 grid gap-4" onSubmit={onSubmit}>
          <Field label="Name">
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Email">
            <input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Specialty">
            <input className={inputClass} value={specialty} onChange={(e) => setSpecialty(e.target.value)} required />
          </Field>
          <Field label="License number">
            <input className={inputClass} value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} required />
          </Field>
          <Field label="Hospital">
            <input className={inputClass} value={hospital} onChange={(e) => setHospital(e.target.value)} />
          </Field>
          <Field label="Date of birth">
            <input className={inputClass} type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} required />
          </Field>
          <Field label="Password">
            <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
          </Field>
          {error ? <p className="text-sm text-severity-high">{error}</p> : null}
          <CtaButton type="submit" disabled={busy || !token}>
            Create profile
          </CtaButton>
          <GhostButton type="button" onClick={() => navigate("/")}>
            Not now
          </GhostButton>
        </form>
        <p className="mt-6 text-xs text-charcoal/45">
          <Link to="/" className="text-mint">
            Back to Hetu
          </Link>
        </p>
      </div>
    </main>
  );
}
