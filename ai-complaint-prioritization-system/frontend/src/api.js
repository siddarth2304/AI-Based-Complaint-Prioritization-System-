const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(error.error || "Request failed");
  }
  return response.json();
}

export const api = {
  health: () => request("/api/health"),
  submitComplaint: (data) =>
    request("/api/complaints", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getComplaints: () => request("/api/complaints"),
  getStats: () => request("/api/complaints/stats"),
  updateStatus: (id, status) =>
    request(`/api/complaints/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  submitRating: (id, rating) =>
    request(`/api/complaints/${id}/rating`, {
      method: "PATCH",
      body: JSON.stringify({ rating }),
    }),
  generateSolution: (id) =>
    request(`/api/complaints/${id}/solution`, {
      method: "POST",
    }),
  askAiAssist: (message) =>
    request("/api/ai/assist", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
