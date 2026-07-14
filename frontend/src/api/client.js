export const API_BASE =
  import.meta.env.VITE_API_BASE ||
  'https://library-data-retrieval-llm-chatbot-619h.onrender.com';

export const Auth = {
  saveAccessToken(token) {
    localStorage.setItem('access_token', token);
  },

  saveTokens(data) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
  },

  getAccessToken() {
    return localStorage.getItem('access_token');
  },

  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  },

  clear() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  isLoggedIn() {
    return Boolean(localStorage.getItem('access_token'));
  },
};

export function routeTo(path) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export function logout() {
  Auth.clear();
  routeTo('/');
}

export async function refreshAccessToken() {
  const refreshToken = Auth.getRefreshToken();

  if (!refreshToken) {
    return false;
  }

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    Auth.clear();
    return false;
  }

  const data = await res.json();
  Auth.saveAccessToken(data.access_token);
  return true;
}

export async function authFetch(url, options = {}) {
  let token = Auth.getAccessToken();
  const requestOptions = {
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  };

  if (token) {
    requestOptions.headers.Authorization = `Bearer ${token}`;
  }

  let response = await fetch(url, requestOptions);

  if (response.status === 401) {
    const refreshed = await refreshAccessToken();

    if (!refreshed) {
      logout();
      return response;
    }

    token = Auth.getAccessToken();
    requestOptions.headers.Authorization = `Bearer ${token}`;
    response = await fetch(url, requestOptions);
  }

  return response;
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Login failed.');
  }

  return data;
}

export async function register(username, email, password) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Registration failed.');
  }

  return data;
}

export async function getCurrentUser() {
  const res = await authFetch(`${API_BASE}/auth/me`);

  if (!res.ok) {
    throw new Error('Could not load current user.');
  }

  return res.json();
}
