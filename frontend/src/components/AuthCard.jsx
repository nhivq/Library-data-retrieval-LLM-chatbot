import { routeTo } from '../api/client.js';

export default function AuthCard({ title, children, footer }) {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <img className="auth-brand-icon" src="/assets/favicon.png" alt="" />
          <div className="auth-brand-name">QuynhNhiVu</div>
          <div className="auth-brand-sub">Open Library AI Book Retrieval</div>
        </div>

        <div className="divider" />
        <h1 className="auth-heading" style={{ marginTop: 20 }}>{title}</h1>
        {children}
        <p className="auth-footer">{footer}</p>
      </div>
    </div>
  );
}

export function AppLink({ to, children }) {
  return (
    <a
      href={to}
      onClick={(event) => {
        event.preventDefault();
        routeTo(to);
      }}
    >
      {children}
    </a>
  );
}
