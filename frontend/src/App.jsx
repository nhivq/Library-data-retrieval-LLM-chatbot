import { useEffect, useState } from 'react';
import { Auth, routeTo } from './api/client.js';
import AdminPage from './pages/AdminPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import OAuthSuccessPage from './pages/OAuthSuccessPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';

function normalizePath() {
  const path = window.location.pathname;

  if (path.endsWith('/register.html')) return '/register';
  if (path.endsWith('/chat.html')) return '/chat';
  if (path.endsWith('/admin.html')) return '/admin';
  if (path.endsWith('/oauth_success.html')) return '/oauth-success';

  return path;
}

export default function App() {
  const [path, setPath] = useState(normalizePath());

  useEffect(() => {
    const onPopState = () => setPath(normalizePath());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    const publicRoutes = ['/', '/register', '/oauth-success'];

    if (!Auth.isLoggedIn() && !publicRoutes.includes(path)) {
      routeTo('/');
    }

    if (Auth.isLoggedIn() && (path === '/' || path === '/register')) {
      routeTo('/chat');
    }
  }, [path]);

  if (path === '/register') return <RegisterPage />;
  if (path === '/oauth-success') return <OAuthSuccessPage />;
  if (path === '/admin') return <AdminPage />;
  if (path === '/chat') return <ChatPage />;

  return <LoginPage />;
}
