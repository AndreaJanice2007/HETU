import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import BrandMark from "../components/BrandMark";
import ComparisonCards from "../components/ComparisonCards";
import { CtaButton, Field, GhostButton, inputClass } from "../ui";

const CHOICES = [
  { id: "agree_a", label: "Agree with Dr. A" },
  { id: "agree_b", label: "Agree with Dr. B" },
  { id: "independent", label: "Provide independent diagnosis" },
];

export default function GuestJudge() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [payload, setPayload] = useState(null);
  const [choice, setChoice] = useState("");
  const [explanation, setExplanation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [declinedSignup, setDeclinedSignup] = useState(false);

  useEffect(() => {
    api
      .guestJudge(token)
      .then(setPayload)
      .catch((err) => setError(err.message));
  }, [token]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      setPayload(await api.submitGuestJudgment(token, { choice, explanation }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const flag = payload?.flag;
  const judged = payload?.status === "judged";
  const inviterName = payload?.invited_by?.name;
  const verified = Boolean(payload?.verified ?? payload?.license_verified);

  return (
    <main className="relative z-10 min-h-screen bg-offwhite px-5 py-12 text-charcoal">
      <div className="mx-auto w-full max-w-3xl">
        <BrandMark size="md" className="mb-8" />

        {judged ? (
          <section className="rounded-[12px] bg-white p-8 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8">
            <h1 className="text-2xl font-semibold leading-snug">Thank you for your judgment.</h1>
            <p className="mt-3 text-[15px] leading-relaxed text-charcoal/70">
              Would you like to create a full Hetu profile? Your credibility score will start with
              the case you just resolved.
            </p>
            {declinedSignup ? (
              <p className="mt-6 text-sm text-charcoal/60">
                No account was created. Your judgment stays on this flag as a permanent record.
              </p>
            ) : (
              <div className="mt-8 flex flex-wrap gap-3">
                <CtaButton
                  type="button"
                  onClick={() => navigate(`/doctor/signup?prefill_token=${token}`)}
                >
                  Create My Hetu Profile
                </CtaButton>
                <GhostButton type="button" onClick={() => setDeclinedSignup(true)}>
                  Not now
                </GhostButton>
              </div>
            )}
          </section>
        ) : (
          <>
            <h1 className="max-w-2xl text-3xl font-semibold leading-tight">
              You've been invited to help resolve a diagnostic disagreement
            </h1>
            <p className="mt-3 max-w-2xl text-sm italic text-charcoal/55">
              {payload?.disclaimer || "Hetu does not diagnose. This is a suggestion, not a verdict."}
            </p>

            {payload ? (
              <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    verified ? "bg-mint/15 text-mint" : "bg-charcoal/8 text-charcoal/60"
                  }`}
                >
                  {verified ? "License verified" : "License pending"}
                </span>
                {inviterName ? (
                  <span className="text-charcoal/55">Invited by {inviterName}</span>
                ) : null}
              </div>
            ) : null}

            {error ? <p className="mt-4 text-sm text-severity-high">{error}</p> : null}

            {flag ? (
              <div className="mt-8">
                <ComparisonCards diagnosisA={flag.diagnosis_1} diagnosisB={flag.diagnosis_2} />
                <form className="mt-8 grid gap-5 rounded-[12px] bg-white p-6 shadow-[0_8px_24px_rgba(43,45,47,0.06)] ring-1 ring-charcoal/8" onSubmit={submit}>
                  <fieldset className="grid gap-3">
                    <legend className="text-sm font-medium">Your judgment</legend>
                    {CHOICES.map((item) => (
                      <label
                        key={item.id}
                        className={`flex cursor-pointer items-center gap-3 rounded-[10px] px-3 py-3 ring-1 ${
                          choice === item.id ? "bg-mint/10 ring-mint" : "bg-offwhite ring-charcoal/10"
                        }`}
                      >
                        <input
                          type="radio"
                          name="judgment"
                          value={item.id}
                          checked={choice === item.id}
                          onChange={() => setChoice(item.id)}
                          required
                          className="accent-[#02c39a]"
                        />
                        <span className="text-sm">{item.label}</span>
                      </label>
                    ))}
                  </fieldset>
                  <Field label="Explanation">
                    <textarea
                      className={`${inputClass} min-h-28`}
                      value={explanation}
                      onChange={(e) => setExplanation(e.target.value)}
                      required
                    />
                  </Field>
                  <CtaButton type="submit" disabled={busy || !choice}>
                    Submit judgment
                  </CtaButton>
                </form>
              </div>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
