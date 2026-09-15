import { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import AppShell, { Tabs } from "../components/AppShell";
import { ConsentCenter, CorrectionForm, ExplainerView, RecordsTimeline } from "../components/CarePanels";
import SendReport from "../components/SendReport";
import { buildReport } from "../medreaStore";

export default function SurrogateView() {
  const { session } = useAuth();
  const [params, setParams] = useSearchParams();
  const patient = session?.surrogate?.linked_patient;
  const [tab, setTab] = useState(params.get("tab") || "records");
  const [diagnoses, setDiagnoses] = useState([]);
  const [access, setAccess] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [explainer, setExplainer] = useState(null);
  const [flags, setFlags] = useState([]);
  const [field, setField] = useState("conditions");
  const [proposed, setProposed] = useState("");
  const [error, setError] = useState("");

  const disclosed = diagnoses.filter((d) => d.disclose_to_patient);
  const notified = diagnoses.filter((d) => !d.disclose_to_patient);

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
  if (session.user.role !== "surrogate") {
    return <Navigate to={session.user.role === "doctor" ? "/doctor" : "/patient"} replace />;
  }

  const tabs = [
    { id: "records", label: "Records" },
    { id: "notified", label: "Notified Diagnoses" },
    { id: "explainer", label: "AI Explainer" },
    { id: "consent", label: "Consent Center" },
    { id: "correction", label: "Suggest Correction" },
  ];

  return (
    <AppShell title={`${session.surrogate?.relationship} · ${patient?.name}`} role="surrogate">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-charcoal/55">
          You act for {patient?.name}. Write-actions on this account cover that patient.
        </p>
        <SendReport
          userId={session.user.id}
          report={buildReport({
            role: "surrogate",
            patientName: patient?.name,
            diagnoses,
            flags,
            access,
          })}
        />
      </div>
      <Tabs tabs={tabs} active={tab} onChange={chooseTab} />
      {tab === "records" ? <RecordsTimeline diagnoses={disclosed} empty="No disclosed records yet." /> : null}
      {tab === "notified" ? (
        <section className="rounded-xl border border-charcoal/20 bg-offwhite p-6">
          <div className="mb-4 inline-flex rounded-[10px] bg-charcoal px-2.5 py-1 text-xs font-medium text-offwhite">
            Sensitive — notified to surrogate
          </div>
          <RecordsTimeline diagnoses={notified} empty="No surrogate-only notifications yet." />
        </section>
      ) : null}
      {tab === "explainer" ? <ExplainerView explainer={explainer} /> : null}
      {tab === "consent" ? <ConsentCenter access={access} canWrite onDecide={decide} /> : null}
      {tab === "correction" ? (
        <CorrectionForm
          canWrite
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
