const chatKey = (userId) => `hetu-medrea-${userId}`;
const reportKey = (userId) => `hetu-medrea-report-${userId}`;

export function loadMedreaMessages(userId) {
  if (!userId) return [];
  try {
    return JSON.parse(sessionStorage.getItem(chatKey(userId)) || "[]");
  } catch {
    return [];
  }
}

export function saveMedreaMessages(userId, messages) {
  if (!userId) return;
  sessionStorage.setItem(chatKey(userId), JSON.stringify(messages));
}

export function queueMedreaReport(userId, report) {
  if (!userId) return;
  sessionStorage.setItem(reportKey(userId), JSON.stringify(report));
}

export function takeMedreaReport(userId) {
  if (!userId) return null;
  const raw = sessionStorage.getItem(reportKey(userId));
  sessionStorage.removeItem(reportKey(userId));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function buildReport({ role, patientName, diagnoses = [], flags = [], access = [] }) {
  return {
    role,
    patient_name: patientName,
    diagnoses: diagnoses.map((d) => ({
      diagnosis_label: d.diagnosis_label,
      doctor: d.doctor?.name,
      disclose_to_patient: d.disclose_to_patient,
    })),
    flags: flags.map((f) => ({
      status: f.status,
      severity: f.severity,
      root_cause: f.root_cause,
    })),
    access: access.map((a) => ({
      doctor: a.doctor?.name,
      status: a.status,
    })),
  };
}

export function reportAsMessage(report) {
  const labels = (report.diagnoses || [])
    .map((d) => d.diagnosis_label)
    .filter(Boolean)
    .join(", ");
  const open = (report.flags || []).filter((f) => f.status !== "resolved").length;
  return (
    `Report from ${report.role} view for ${report.patient_name}. ` +
    `Diagnoses: ${labels || "none listed"}. ` +
    `Open flags: ${open}.`
  );
}
