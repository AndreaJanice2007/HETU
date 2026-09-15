import { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import AppShell, { Tabs } from "../components/AppShell";
import { ConsentCenter, CorrectionForm, ExplainerView, RecordsTimeline } from "../components/CarePanels";
import SendReport from "../components/SendReport";
import { buildReport } from "../medreaStore";

export default function PatientView() {
  const { session } = useAuth();
  const [params, setParams] = useSearchParams();
  const isMinor = session?.user?.is_minor;
  const patient = session?.patient;
  const [tab, setTab] = useState(params.get("tab") || "records");
  const [diagnoses, setDiagnoses] = useState([]);
  const [access, setAccess] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [explainer, setExplainer] = useState(null);
  const [flags, setFlags] = useState([]);
  const [field, setField] = useState("conditions");
  const [proposed, setProposed] = useState("");
  const [error, setError] = useState("");

  async function reload() {
    const [dx, acc, cor, exp, fl] = await Promise.all([
      api.diagnoses(patient.id),
      api.access(),
      api.corrections(patient.id),
      api.explainer(),
      api.flags(patient.id),
    ]);
    setDiagnoses(dx);
    setAccess(acc);
    setCorrections(cor);
    setExplainer(exp);
    setFlags(fl);
  }

  useEffect(() => {
    if (!patient?.id) return;
    reload().catch((err) => setError(err.message));
  }, [patient?.id]);

  useEffect(() => {
    const next = params.get("tab");
    if (next) setTab(next);
  }, [params]);

  function chooseTab(id) {
    setTab(id);
    setParams({ tab: id });
  }

  async function suggest(e) {
    e.preventDefault();
    try {
      await api.suggestCorrection({ patient_id: patient.id, field, proposed_value: proposed });
      setProposed("");
      await reload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function decide(id, approve) {
    try {
      if (approve) await api.approveAccess(id);
      else await api.denyAccess(id);
      await reload();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!session?.user) return <Navigate to="/" replace />;
  if (session.user.role !== "patient") {
    return <Navigate to={`/${session.user.role}`} replace />;
  }

  const tabs = [
    { id: "records", label: "Records" },
    { id: "explainer", label: "AI Explainer" },
    { id: "consent", label: "Consent Center" },
    { id: "correction", label: "Suggest Correction" },
  ];

  return (
    <AppShell title={patient?.name} role="patient">
      <div className="mb-6 flex flex-wrap items-center justify-end">
        <SendReport
          userId={session.user.id}
          report={buildReport({
            role: "patient",
            patientName: patient?.name,
            diagnoses,
            flags,
            access,
          })}
        />
      </div>
      {isMinor ? (
        <p className="mb-6 rounded-xl bg-charcoal/5 px-4 py-3 text-sm text-charcoal/70">
          View-only account. Your surrogate manages corrections and doctor access.
        </p>
      ) : null}
      <Tabs tabs={tabs} active={tab} onChange={chooseTab} />
      {tab === "records" ? (
        <RecordsTimeline diagnoses={diagnoses} empty="No records yet." />
      ) : null}
      {tab === "explainer" ? <ExplainerView explainer={explainer} /> : null}
      {tab === "consent" ? (
        <ConsentCenter access={access} canWrite={!isMinor} onDecide={decide} />
      ) : null}
      {tab === "correction" ? (
        <CorrectionForm
          canWrite={!isMinor}
          field={field}
          setField={setField}
          proposed={proposed}
          setProposed={setProposed}
          corrections={corrections}
          onSubmit={suggest}
        />
      ) : null}
      {error ? <p className="mt-6 text-sm text-severity-high">{error}</p> : null}
    </AppShell>
  );
}
