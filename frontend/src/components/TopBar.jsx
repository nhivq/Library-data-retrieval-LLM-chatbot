import { logout, routeTo } from '../api/client.js';

export default function TopBar({ title = 'QuynhNhiVu', subtitle, showAdminLink, chatLink }) {
  return (
    <header className="topbar">
      <div className="brand">
        <img className="brand-icon" src="/assets/favicon.png" alt="" />
        <span className="brand-name">{title}</span>
      </div>
      {subtitle && <span className="brand-sub">{subtitle}</span>}
      {showAdminLink && (
        <a
          className="topbar-link"
          href="/admin"
          onClick={(event) => {
            event.preventDefault();
            routeTo('/admin');
          }}
        >
          Dashboard
        </a>
      )}
      {chatLink && (
        <a
          className="topbar-link"
          href="/chat"
          onClick={(event) => {
            event.preventDefault();
            routeTo('/chat');
          }}
        >
          Chat
        </a>
      )}
      <button className="logout-btn" type="button" onClick={logout}>
        Logout
      </button>
    </header>
  );
}
