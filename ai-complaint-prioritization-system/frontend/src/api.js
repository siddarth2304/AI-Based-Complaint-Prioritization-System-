const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";
const TOKEN_KEY = "secureComplaintJwt";

let unauthorizedHandler = null;
let forbiddenHandler = null;

export function setAuthHandlers({ onUnauthorized, onForbidden } = {}) {
  unauthorizedHandler = onUnauthorized || null;
  forbiddenHandler = onForbidden || null;
}

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (error) {
    const networkError = new Error("Cannot connect to server. Please check backend is running.");
    networkError.cause = error;
    throw networkError;
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.error || safeStatusMessage(response.status);
    if (response.status === 401 && unauthorizedHandler) unauthorizedHandler(message);
    if (response.status === 403 && forbiddenHandler) forbiddenHandler(message);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function safeStatusMessage(status) {
  if (status === 401) return "Invalid email or password.";
  if (status === 403) return "Access denied.";
  if (status === 429) return "Too many requests. Please try again later.";
  if (status >= 500) return "Server error. Please try again later.";
  return "Request failed.";
}

export const api = {
  health: () => request("/api/health"),
  login: (data) => request("/api/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (data) => request("/api/auth/register", { method: "POST", body: JSON.stringify(data) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),
  seedDemo: () => request("/api/demo/seed", { method: "POST" }),
  submitComplaint: (data) => request("/api/complaints", { method: "POST", body: JSON.stringify(data) }),
  getComplaints: () => request("/api/complaints"),
  getComplaint: (id) => request(`/api/complaints/${encodeURIComponent(id)}`),
  getStats: () => request("/api/complaints/stats"),
  updateStatus: (id, status, staffNote = "") =>
    request(`/api/complaints/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, staffNote }),
    }),
  assignComplaint: (id, staffId) =>
    request(`/api/complaints/${encodeURIComponent(id)}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ staffId }),
    }),
  submitRating: (id, rating) =>
    request(`/api/complaints/${encodeURIComponent(id)}/rating`, {
      method: "PATCH",
      body: JSON.stringify({ rating }),
    }),
  generateSolution: (id) => request(`/api/complaints/${encodeURIComponent(id)}/solution`, { method: "POST" }),
  askAiAssist: (message) => request("/api/ai/assist", { method: "POST", body: JSON.stringify({ message }) }),
  getUsers: () => request("/api/admin/users"),
  updateUser: (uid, data) => request(`/api/admin/users/${encodeURIComponent(uid)}`, { method: "PATCH", body: JSON.stringify(data) }),
  getAuditLogs: () => request("/api/admin/audit-logs"),
  getSecurityEvents: () => request("/api/admin/security-events"),
};
