// ── Config ────────────────────────────────────────────────────
const API_BASE = "https://library-data-retrieval-llm-chatbot-619h.onrender.com";

// ── Reusable authenticated fetch ──────────────────────────────
async function authFetch(
    url,
    options={}
)
{
  let token = Auth.getAccessToken();

  options.headers = {
    ...(options.headers || {})
  };

  if(token){
    options.headers.Authorization = `Bearer ${token}`;
  }


  let response = await fetch(
        url,
        options
      );

  if(response.status === 401){const refreshed = await refreshAccessToken();

    if(!refreshed){
      logout();
      return response;
    }

    token = Auth.getAccessToken();

    options.headers.Authorization = `Bearer ${token}`;

    response = await fetch(
        url,
        options
      );
  }

  return response;
}

// ── Storage helpers ───────────────────────────────────────────
const Auth = {

  saveAccessToken:(token)=>{
    localStorage.setItem(
      "access_token",
      token
    );
  },

  saveTokens: (data) => {
    localStorage.setItem(
      "access_token",
      data.access_token
    );

    localStorage.setItem(
      "refresh_token",
      data.refresh_token
    );
  },

  getAccessToken: () => {
    return localStorage.getItem("access_token");
  },

  getRefreshToken: () => {
    return localStorage.getItem("refresh_token");
  },

  clear: () => {localStorage.removeItem("access_token");

    localStorage.removeItem("refresh_token");
  },

  isLoggedIn: () => {
    return !!localStorage.getItem("access_token");
  }
};

// ── API service ───────────────────────────────────────────────
// When you add JWT later:
//   1. Save token: sessionStorage.setItem('token', data.access_token)
//   2. Add headers: 'Authorization': `Bearer ${sessionStorage.getItem('token')}`
const ApiService = {
  async login(username, password) {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok)
      throw new Error(data.detail || data.message || "Login failed.");
    return data; // { message, user_id }
  },

  async register(username, email, password) {
    const res = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await res.json();
    if (!res.ok)
      throw new Error(data.detail || data.message || "Registration failed.");
    return data; // { message }
  },
};

// ── Refresh function ──────────────────────────────────────────
async function refreshAccessToken(){

  const refreshToken = Auth.getRefreshToken();

  if(!refreshToken)
    return false;

  const res = await fetch(`${API_BASE}/refresh`,
    {
      method:"POST",

      headers:{"Content-Type":"application/json"},

      body:JSON.stringify({refresh_token:refreshToken})
    }
  );

  if(!res.ok){

    Auth.clear();

    return false;
  }

  const data = await res.json();

   Auth.saveAccessToken(
        data.access_token
    );

  return true;
}

// ── UI helpers ────────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById("errorMsg");
  const ok = document.getElementById("successMsg");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  ok.classList.remove("show");
}

function showSuccess(msg) {
  const el = document.getElementById("successMsg");
  const err = document.getElementById("errorMsg");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  err.classList.remove("show");
}

function clearAlerts() {
  document.getElementById("errorMsg")?.classList.remove("show");
  document.getElementById("successMsg")?.classList.remove("show");
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.textContent = loading ? "Please wait…" : btn.dataset.label;
}

function markInvalid(id) {
  document.getElementById(id)?.classList.add("invalid");
}

function clearInvalid() {
  document
    .querySelectorAll(".invalid")
    .forEach((el) => el.classList.remove("invalid"));
}

// ── Auth guard (call at top of chat.html) ─────────────────────
function requireAuth() {
  const onLoginPage = window.location.pathname.endsWith("index.html");
  const onRegisterPage = window.location.pathname.endsWith("register.html");
  if (!Auth.isLoggedIn() && !onLoginPage && !onRegisterPage) {
    window.location.replace("index.html");
  }
}

// ── Logout ────────────────────────────────────────────────────
function logout() {
  Auth.clear();
  window.location.href = "index.html";
}

// ── Login page init ───────────────────────────────────────────
function initLogin() {
  // If already logged in, skip to chat
  if (Auth.isLoggedIn()) {
    window.location.href = "chat.html";
    return;
  }

  const form = document.getElementById("loginForm");
  const submitBtn = document.getElementById("submitBtn");
  submitBtn.dataset.label = "Login";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlerts();
    clearInvalid();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    // Client-side validation
    let hasError = false;
    if (!username) {
      markInvalid("username");
      hasError = true;
    }
    if (!password) {
      markInvalid("password");
      hasError = true;
    }
    if (hasError) {
      showError("Please fill in all fields.");
      return;
    }

    setLoading(submitBtn, true);

    try {
      const data = await ApiService.login(username, password);
      Auth.saveTokens(data);
      window.location.href = "chat.html";
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(submitBtn, false);
    }
  });
}

// ── Register page init ────────────────────────────────────────
function initRegister() {
  // If already logged in, skip to chat
  if (Auth.isLoggedIn()) {
    window.location.href = "chat.html";
    return;
  }

  const form = document.getElementById("registerForm");
  const submitBtn = document.getElementById("submitBtn");
  submitBtn.dataset.label = "Register";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlerts();
    clearInvalid();

    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    // Client-side validation
    let hasError = false;
    if (!username) {
      markInvalid("username");
      hasError = true;
    }
    if (!email) {
      markInvalid("email");
      hasError = true;
    }
    if (!password) {
      markInvalid("password");
      hasError = true;
    }
    if (!confirmPassword) {
      markInvalid("confirmPassword");
      hasError = true;
    }

    if (hasError) {
      showError("Please fill in all fields.");
      return;
    }

    if (password !== confirmPassword) {
      markInvalid("password");
      markInvalid("confirmPassword");
      showError("Passwords do not match.");
      return;
    }

    setLoading(submitBtn, true);

    try {
      await ApiService.register(username, email, password);
      showSuccess("Account created! Redirecting to login…");
      setTimeout(() => (window.location.href = "index.html"), 1800);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(submitBtn, false);
    }
  });
}
