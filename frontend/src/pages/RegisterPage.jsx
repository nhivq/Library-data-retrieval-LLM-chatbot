import { useState } from 'react';
import { register, routeTo } from '../api/client.js';
import AuthCard, { AppLink } from '../components/AuthCard.jsx';

export default function RegisterPage() {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (!form.username.trim() || !form.email.trim() || !form.password || !form.confirmPassword) {
      setError('Please fill in all fields.');
      return;
    }

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      await register(form.username.trim(), form.email.trim(), form.password);
      setSuccess('Account created! Redirecting to login...');
      setTimeout(() => routeTo('/'), 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const missing = (field) => error === 'Please fill in all fields.' && !form[field];

  return (
    <AuthCard
      title="Create an account"
      footer={<>Already have an account? <AppLink to="/">Login</AppLink></>}
    >
      <div className={`alert alert-error${error ? ' show' : ''}`}>{error}</div>
      <div className={`alert alert-success${success ? ' show' : ''}`}>{success}</div>
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            className={missing('username') ? 'invalid' : ''}
            id="username"
            name="username"
            type="text"
            placeholder="choose a username"
            autoComplete="username"
            value={form.username}
            onChange={(event) => setForm({ ...form, username: event.target.value })}
          />
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            className={missing('email') ? 'invalid' : ''}
            id="email"
            name="email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            className={missing('password') || error === 'Passwords do not match.' ? 'invalid' : ''}
            id="password"
            name="password"
            type="password"
            placeholder="password"
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
          />
        </div>

        <div className="field">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input
            className={missing('confirmPassword') || error === 'Passwords do not match.' ? 'invalid' : ''}
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            placeholder="password"
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={(event) => setForm({ ...form, confirmPassword: event.target.value })}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Please wait...' : 'Register'}
        </button>
      </form>
    </AuthCard>
  );
}
