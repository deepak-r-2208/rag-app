import { createContext, useCallback, useContext, useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'ragnify_token';

const AuthContext = createContext(null);

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
  return res.json();
}

function postJSON(path, body) {
  return handle(
    fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => r),
  );
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async (token) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) {
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
        return;
      }
      setUser(await res.json());
    } catch {
      // Backend unreachable — treat as logged out rather than crashing the app.
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) loadMe(token).finally(() => setLoading(false));
    else setLoading(false);
  }, [loadMe]);

  // Returns { message, verification_code, dev_note } — there's no email
  // service configured, so the code comes back directly in the response
  // instead of being emailed (see backend/app/routers/auth.py).
  const signUp = useCallback((email, password, name) => postJSON('/auth/signup', { name, email, password }), []);

  const verifyEmail = useCallback(async (email, code) => {
    const data = await postJSON('/auth/verify', { email, code });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
  }, []);

  const resendCode = useCallback((email) => postJSON('/auth/resend', { email }), []);

  // Returns either { access_token, user, needs_verification: false } or
  // { needs_verification: true, verification_code } if the account hasn't
  // been verified yet — the caller (AuthPage) decides what to show.
  const signIn = useCallback(async (email, password) => {
    const data = await postJSON('/auth/login', { email, password });
    if (data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setUser(data.user);
    }
    return data;
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  const value = { user, loading, signUp, verifyEmail, resendCode, signIn, signOut };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
