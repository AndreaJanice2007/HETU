const KEY = "hetu-user";

export function getSession() {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setSession(payload) {
  localStorage.setItem(KEY, JSON.stringify(payload));
}

export function clearSession() {
  localStorage.removeItem(KEY);
}

function errorFromDetail(detail) {
  if (!detail) return "Request failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  if (typeof detail === "object") {
    return detail.message || detail.error || JSON.stringify(detail);
  }
  return "Request failed";
}

async function request(path, { method = "GET", body, userId } = {}) {
  const session = getSession();
  const headers = { "Content-Type": "application/json" };
  const id = userId ?? session?.user?.id;
  if (id) headers["X-User-Id"] = String(id);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(errorFromDetail(data.detail));
    }
    return data;
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error("The server did not respond. Try again in a moment.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function uploadFile(path, file) {
  const session = getSession();
  const headers = {};
  if (session?.user?.id) headers["X-User-Id"] = String(session.user.id);
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(path, { method: "POST", headers, body });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(errorFromDetail(data.detail));
  }
  return data;
}

async function uploadForm(path, formData) {
  const session = getSession();
  const headers = {};
  if (session?.user?.id) headers["X-User-Id"] = String(session.user.id);
  const res = await fetch(path, { method: "POST", headers, body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(errorFromDetail(data.detail));
  }
  return data;
}

export const api = {
  login: (identifier, password) =>
    request("/api/login", { method: "POST", body: { identifier, email: identifier, password } }),
  signup: (body) => request("/api/signup", { method: "POST", body }),
  me: () => request("/api/me"),
  explainer: () => request("/api/explainer"),
  patients: () => request("/api/patients"),
  patient: (id) => request(`/api/patients/${id}`),
  catalog: () => request("/api/catalog/diagnoses"),
  access: () => request("/api/access-requests"),
  requestAccess: (patient_id) => request("/api/access-requests", { method: "POST", body: { patient_id } }),
  approveAccess: (id) => request(`/api/access-requests/${id}/approve`, { method: "POST" }),
  denyAccess: (id) => request(`/api/access-requests/${id}/deny`, { method: "POST" }),
  diagnoses: (patient_id) => request(`/api/diagnoses?patient_id=${patient_id}`),
  logDiagnosis: (body) => request("/api/diagnoses", { method: "POST", body }),
  flags: (patient_id) => request(patient_id ? `/api/flags?patient_id=${patient_id}` : "/api/flags"),
  reviewFlag: (id) => request(`/api/flags/${id}/review`, { method: "POST" }),
  resolveFlag: (id, resolution_note) =>
    request(`/api/flags/${id}/resolve`, { method: "POST", body: { resolution_note } }),
  notifications: () => request("/api/notifications"),
  readNotification: (id) => request(`/api/notifications/${id}/read`, { method: "POST" }),
  corrections: (patient_id) => request(`/api/corrections?patient_id=${patient_id}`),
  suggestCorrection: (body) => request("/api/corrections", { method: "POST", body }),
  medreaChat: (body) => request("/api/medrea/chat", { method: "POST", body }),
  extractDocument: (file) => uploadFile("/api/documents/extract", file),
  inviteGuestJudge: (flag_id, body) =>
    request(`/api/flags/${flag_id}/invite-external-doctor`, { method: "POST", body }),
  guestInvites: (flag_id) => request(`/api/flags/${flag_id}/guest-judge-invites`),
  judgePool: (flag_id) => request(`/api/flags/${flag_id}/judge-pool`),
  guestJudge: (token) => request(`/api/guest-judge/${token}`),
  guestJudgePrefill: (token) => request(`/api/guest-judge/${token}/prefill`),
  verifyGuestLicense: (token, license_number) =>
    request(`/api/guest-judge/${token}/verify-license`, { method: "POST", body: { license_number } }),
  submitGuestJudgment: (token, body) =>
    request(`/api/guest-judge/${token}/judge`, { method: "POST", body }),
  doctorSignup: (body) => request("/api/doctor/signup", { method: "POST", body }),
  searchPatients: (q) => request(`/api/patients/search?q=${encodeURIComponent(q)}`),
  reports: (patient_id) => request(`/api/reports?patient_id=${patient_id}`),
  doctors: () => request("/api/doctors"),
  timeline: (patient_id) => request(patient_id ? `/api/timeline?patient_id=${patient_id}` : "/api/timeline"),
  careCircle: (patient_id) =>
    request(patient_id ? `/api/care-circle?patient_id=${patient_id}` : "/api/care-circle"),
  uploadReport: (formData) => uploadForm("/api/reports", formData),
  gapResponse: (flag_id, body) => request(`/api/flags/${flag_id}/gap-response`, { method: "POST", body }),
  conversations: () => request("/api/conversations"),
  conversation: (id) => request(`/api/conversations/${id}`),
  submitAvailability: (id, slots) =>
    request(`/api/conversations/${id}/availability`, { method: "POST", body: { slots } }),
  addConversationNote: (id, body) =>
    request(`/api/conversations/${id}/notes`, { method: "POST", body: { body } }),
  completeConversation: (id, body) =>
    request(`/api/conversations/${id}/complete`, { method: "POST", body }),
  doctorRank: () => request("/api/doctors/rank"),
  reportFile: async (url) => {
    const session = getSession();
    const headers = {};
    if (session?.user?.id) headers["X-User-Id"] = String(session.user.id);
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error("Could not load the attached file");
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};
