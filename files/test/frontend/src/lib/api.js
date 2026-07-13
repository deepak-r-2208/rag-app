const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'ragnify_token';

function authHeaders(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => handle(fetch(`${API_BASE}${path}`, { headers: authHeaders() })),

  post: (path, body) =>
    handle(
      fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      }),
    ),

  put: (path, body) =>
    handle(
      fetch(`${API_BASE}${path}`, {
        method: 'PUT',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      }),
    ),

  delete: (path) => handle(fetch(`${API_BASE}${path}`, { method: 'DELETE', headers: authHeaders() })),

  upload: (path, formData) =>
    handle(
      fetch(`${API_BASE}${path}`, {
        method: 'POST',
        // No Content-Type here — the browser sets the multipart boundary itself.
        headers: authHeaders(),
        body: formData,
      }),
    ),
};
