import {
  API_BASE_URL,
  clearAuthSession,
  clearPendingVerification,
  replaceAnalyses,
  setAuthSession,
  setPendingVerification,
  setVerificationMessage,
  state
} from "./state.js";

const USERS_KEY = "jobfit-users";

export async function registerUser({ name, email, password }) {
  const payload = validateCredentials({ name, email, password, requireName: true });
  if (payload.error) {
    return setAuthError(payload.error);
  }

  try {
    const session = await requestAuth("/api/auth/register", payload);
    setPendingVerification({
      email: session.email,
      verificationId: session.verificationId,
      expiresAt: session.expiresAt,
      devOtp: session.devOtp || "",
      otpSent: Boolean(session.otpSent)
    });
    return { ok: true, verification: state.verification.pending };
  } catch (error) {
    return setAuthError(error.message);
  }
}

export async function loginUser({ email, password }) {
  const payload = validateCredentials({ email, password, requireName: false });
  if (payload.error) {
    return setAuthError(payload.error);
  }

  try {
    const session = await requestAuth("/api/auth/login", payload);
    setAuthSession(session);
    await loadRemoteAnalyses();
    return { ok: true, user: state.auth.user };
  } catch (error) {
    if (String(error.message || "").includes("Email belum diverifikasi")) {
      try {
        const response = await requestAuth("/api/auth/resend-otp", {
          email: payload.email
        });
        setPendingVerification({
          email: response.email,
          verificationId: response.verificationId,
          expiresAt: response.expiresAt,
          devOtp: response.devOtp || "",
          otpSent: Boolean(response.otpSent)
        });
        return { ok: false, needsVerification: true };
      } catch (resendError) {
        return setAuthError(resendError.message);
      }
    }

    const legacyUser = findLegacyUser(payload.email, payload.password);
    if (!legacyUser) {
      return setAuthError(error.message);
    }

    try {
      const session = await requestAuth("/api/auth/register", {
        name: legacyUser.name,
        email: payload.email,
        password: payload.password
      });
      setPendingVerification({
        email: session.email,
        verificationId: session.verificationId,
        expiresAt: session.expiresAt,
        devOtp: session.devOtp || "",
        otpSent: Boolean(session.otpSent)
      });
      return { ok: false, needsVerification: true };
    } catch (syncError) {
      return setAuthError(syncError.message);
    }
  }
}

export async function verifyOtp({ otp }) {
  const pending = state.verification.pending;
  if (!pending?.verificationId || !pending?.email) {
    return setVerificationError("Data verifikasi tidak ditemukan. Silakan daftar ulang.");
  }

  const normalizedOtp = String(otp || "").trim();
  if (!/^\d{6}$/.test(normalizedOtp)) {
    return setVerificationError("Masukkan kode OTP 6 digit.");
  }

  try {
    const session = await requestAuth("/api/auth/verify-otp", {
      verificationId: pending.verificationId,
      email: pending.email,
      otp: normalizedOtp
    });
    clearPendingVerification();
    setAuthSession(session);
    await loadRemoteAnalyses();
    return { ok: true, user: state.auth.user };
  } catch (error) {
    return setVerificationError(error.message);
  }
}

export async function resendOtp() {
  const pending = state.verification.pending;
  if (!pending?.email) {
    return setVerificationError("Email verifikasi tidak ditemukan. Silakan daftar ulang.");
  }

  try {
    const response = await requestAuth("/api/auth/resend-otp", {
      email: pending.email
    });
    setPendingVerification({
      email: response.email,
      verificationId: response.verificationId,
      expiresAt: response.expiresAt,
      devOtp: response.devOtp || "",
      otpSent: Boolean(response.otpSent)
    });
    return { ok: true, verification: state.verification.pending };
  } catch (error) {
    return setVerificationError(error.message);
  }
}

export async function restoreSession() {
  if (!state.auth.token) {
    return { ok: false };
  }

  try {
    const response = await apiFetch("/api/auth/me");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(getApiErrorMessage(payload));
    }

    setAuthSession({
      user: payload.user,
      token: state.auth.token
    });
    await loadRemoteAnalyses();
    return { ok: true, user: state.auth.user };
  } catch (error) {
    clearAuthSession();
    return { ok: false, error: error.message };
  }
}

export async function logoutUser() {
  if (state.auth.token) {
    await apiFetch("/api/auth/logout", { method: "POST" }).catch(() => null);
  }

  clearAuthSession();
  clearAccountSettingsMessage();
}

export async function updateAccountProfile({ name }) {
  const normalizedName = String(name || "").trim();

  if (normalizedName.length < 2) {
    return setAccountSettingsError("Nama wajib diisi minimal 2 karakter.");
  }

  try {
    const response = await apiFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: normalizedName })
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getApiErrorMessage(payload));
    }

    setAuthSession({
      user: payload.user,
      token: state.auth.token
    });
    return setAccountSettingsSuccess("Profil akun berhasil diperbarui.");
  } catch (error) {
    return setAccountSettingsError(error.message);
  }
}

export async function changePassword({ currentPassword, newPassword, confirmPassword }) {
  try {
    const response = await apiFetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currentPassword, newPassword, confirmPassword })
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getApiErrorMessage(payload));
    }

    return setAccountSettingsSuccess("Password berhasil diganti.");
  } catch (error) {
    return setAccountSettingsError(error.message);
  }
}

export function clearAuthError() {
  state.auth.error = "";
}

export function clearVerificationMessage() {
  setVerificationMessage({ error: "", success: "" });
}

export function clearAccountSettingsMessage() {
  state.accountSettings = {
    error: "",
    success: ""
  };
}

async function requestAuth(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(getApiErrorMessage(data));
  }

  return data;
}

function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.auth.token) {
    headers.set("Authorization", `Bearer ${state.auth.token}`);
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });
}

async function loadRemoteAnalyses() {
  const response = await apiFetch("/api/analyses");
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload));
  }

  replaceAnalyses(Array.isArray(payload.analyses) ? payload.analyses : []);
}

function validateCredentials({ name, email, password, requireName }) {
  const normalizedName = String(name || "").trim();
  const normalizedEmail = normalizeEmail(email);
  const normalizedPassword = String(password || "");

  if (requireName && normalizedName.length < 2) {
    return { error: "Nama wajib diisi minimal 2 karakter." };
  }

  if (!isValidEmail(normalizedEmail)) {
    return { error: "Masukkan alamat email yang valid." };
  }

  if (normalizedPassword.length < 6) {
    return { error: "Password minimal 6 karakter." };
  }

  return {
    name: normalizedName,
    email: normalizedEmail,
    password: normalizedPassword
  };
}

function setAuthError(message) {
  state.auth.error = message || "Autentikasi gagal diproses.";
  return { ok: false, error: state.auth.error };
}

function setVerificationError(message) {
  setVerificationMessage({
    error: message || "Verifikasi OTP gagal diproses.",
    success: ""
  });
  return { ok: false, error: state.verification.error };
}

function setAccountSettingsError(message) {
  state.accountSettings = {
    error: message || "Pengaturan akun gagal diproses.",
    success: ""
  };
  return { ok: false, error: state.accountSettings.error };
}

function setAccountSettingsSuccess(message) {
  state.accountSettings = {
    error: "",
    success: message
  };
  return { ok: true };
}

function findLegacyUser(email, password) {
  return readUsers().find(
    (item) => normalizeEmail(item.email) === normalizeEmail(email) && item.password === String(password || "")
  );
}

function readUsers() {
  try {
    const rawUsers = window.localStorage.getItem(USERS_KEY);
    const users = rawUsers ? JSON.parse(rawUsers) : [];
    return Array.isArray(users) ? users : [];
  } catch (error) {
    window.localStorage.removeItem(USERS_KEY);
    return [];
  }
}

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function getApiErrorMessage(payload) {
  const detail = payload?.detail || payload?.error;

  if (typeof detail === "string") {
    return detail;
  }

  return "Layanan akun sedang bermasalah. Coba beberapa saat lagi.";
}
