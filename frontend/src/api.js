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

async function request(path, { method = "GET", body, userId } = {}) {
  const session = getSession();
  const headers = { "Content-Type": "application/json" };
  const id = userId ?? session?.user?.id;
  if (id) headers["X-User-Id"] = String(id);
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || "Request failed";
    throw new Error(message);
  }
  return data;
}

export const api = {
  login: (email, password) => request("/api/login", { method: "POST", body: { email, password } }),
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
};
