import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

function Field({ label, ...props }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input {...props} />
    </div>
  );
}

export default function AuthPage() {
  const { signUp, verifyEmail, resendCode, signIn } = useAuth();
  const [pane, setPane] = useState('signin');
  const [pendingEmail, setPendingEmail] = useState('');
  const [devCode, setDevCode] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);

  function switchPane(next) {
    setPane(next);
    setError('');
    setInfo('');
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setError('');
    setInfo('');
    setBusy(true);
    const form = new FormData(e.target);
    const email = form.get('email');
    const password = form.get('password');
    try {
      const data = await signIn(email, password);
      if (data.needs_verification) {
        setPendingEmail(email);
        setDevCode(data.verification_code || '');
        setPane('verify');
        setInfo('Verify your email to finish signing in.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSignUp(e) {
    e.preventDefault();
    setError('');
    setInfo('');
    const form = new FormData(e.target);
    const name = form.get('name');
    const email = form.get('email');
    const password = form.get('password');
    const password2 = form.get('password2');
    if (password !== password2) return setError("Passwords don't match.");
    if (password.length < 6) return setError('Password needs at least 6 characters.');

    setBusy(true);
    try {
      const res = await signUp(email, password, name);
      setPendingEmail(email);
      setDevCode(res.verification_code || '');
      setPane('verify');
      setInfo('Account created — enter the code below to verify.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setError('');
    setInfo('');
    setBusy(true);
    const form = new FormData(e.target);
    try {
      await verifyEmail(pendingEmail, form.get('code'));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setError('');
    setInfo('');
    try {
      const res = await resendCode(pendingEmail);
      setDevCode(res.verification_code || '');
      setInfo('New code generated.');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-shell-wrap">
      <div className="auth-shell">
        <div className="auth-side">
          <div>
            <div className="brandmark">
              <span className="brand-word">
                RAGnify <em>Media</em>
              </span>
            </div>
            <div className="auth-tagline">
              Ask your documents.
              <br />
              Get answers you can <span className="accent">trust</span>.
            </div>
            <ul className="auth-points">
              <li>
                <span className="dot" />
                Every answer is grounded in your own files — nothing is invented.
              </li>
              <li>
                <span className="dot" />
                Upload PDFs, Word docs, scans, spreadsheets, and plain text.
              </li>
              <li>
                <span className="dot" />
                Ask by typing or by voice, and see exactly which passage was used.
              </li>
            </ul>
          </div>
          <div className="auth-foot">RAGnify Media · runs entirely on your own machine, $0</div>
        </div>

        <div className="auth-main">
          {error && <div className="banner banner-error">{error}</div>}
          {info && !error && <div className="banner banner-info">{info}</div>}

          {pane === 'signin' && (
            <form onSubmit={handleSignIn}>
              <h1>Welcome back</h1>
              <p className="auth-sub">Sign in to pick up where you left off.</p>
              <Field label="Email" name="email" type="email" autoComplete="email" required />
              <Field label="Password" name="password" type="password" autoComplete="current-password" required />
              <button className="btn btn-primary" disabled={busy} type="submit">
                Sign in
              </button>
              <div className="auth-switch">
                New here?{' '}
                <button type="button" className="btn-text" onClick={() => switchPane('signup')}>
                  Create an account
                </button>
              </div>
            </form>
          )}

          {pane === 'signup' && (
            <form onSubmit={handleSignUp}>
              <h1>Create your account</h1>
              <p className="auth-sub">Free, and stored only in your own local database.</p>
              <Field label="Full name" name="name" autoComplete="name" required />
              <Field label="Email" name="email" type="email" autoComplete="email" required />
              <div className="field-row">
                <Field label="Password" name="password" type="password" autoComplete="new-password" required />
                <Field label="Confirm" name="password2" type="password" autoComplete="new-password" required />
              </div>
              <button className="btn btn-primary" disabled={busy} type="submit">
                Create account
              </button>
              <div className="auth-switch">
                Already have an account?{' '}
                <button type="button" className="btn-text" onClick={() => switchPane('signin')}>
                  Sign in
                </button>
              </div>
            </form>
          )}

          {pane === 'verify' && (
            <form onSubmit={handleVerify}>
              <h1>Verify your email</h1>
              <p className="auth-sub">
                Enter the 6-digit code for <strong>{pendingEmail}</strong>.
              </p>
              <div className="demo-banner">
                No email service is configured, so the code is shown here directly instead of being
                emailed. See the README if you want to wire up real email later.
              </div>
              {devCode && <div className="dev-code-banner">{devCode}</div>}
              <Field label="Verification code" name="code" inputMode="numeric" maxLength={6} className="verify-input" required />
              <button className="btn btn-primary" disabled={busy} type="submit">
                Verify &amp; continue
              </button>
              <div className="auth-switch">
                Didn't get it?{' '}
                <button type="button" className="btn-text" onClick={handleResend}>
                  Generate a new code
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
