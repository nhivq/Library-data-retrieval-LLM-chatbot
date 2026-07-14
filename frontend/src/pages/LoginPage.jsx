import { useState } from 'react';
import { API_BASE, Auth, login, routeTo } from '../api/client.js';
import AuthCard, { AppLink } from '../components/AuthCard.jsx';

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const invalidUsername = error && !form.username.trim();
  const invalidPassword = error && !form.password;

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!form.username.trim() || !form.password) {
      setError('Please fill in all fields.');
      return;
    }

    setLoading(true);

    try {
      const data = await login(form.username.trim(), form.password);
      Auth.saveTokens(data);
      routeTo('/chat');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      footer={<>Don&apos;t have an account? <AppLink to="/register">Register</AppLink></>}
    >
      <div className={`alert alert-error${error ? ' show' : ''}`}>{error}</div>
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            className={invalidUsername ? 'invalid' : ''}
            id="username"
            name="username"
            type="text"
            placeholder="your username"
            autoComplete="username"
            value={form.username}
            onChange={(event) => setForm({ ...form, username: event.target.value })}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            className={invalidPassword ? 'invalid' : ''}
            id="password"
            name="password"
            type="password"
            placeholder="password"
            autoComplete="current-password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Please wait...' : 'Login'}
        </button>

        <div className="oauth-divider">OR</div>

        <button
          className="google-btn"
          type="button"
          onClick={() => {
            window.location.href = `${API_BASE}/auth/google`;
          }}
        >
          <img
            className="google-icon"
            src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
            alt=""
          />
          Continue with Google
        </button>
      </form>
    </AuthCard>
  );
}
