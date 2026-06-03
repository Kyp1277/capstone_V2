import {
  clearAuthSession,
  clearPendingVerification,
  replaceAnalyses,
  setAuthSession,
  setPendingVerification,
  setVerificationMessage,
  state
} from "./state.js";
import { apiErrorMessage, http } from "./http.js";
import { showToast } from "./utils.js";

export async function registerUser({ name, email, password }) {
  const payload = validateCredentials({ name, email, password, requireName: true });
  if (payload.error) {
    return setAuthError(payload.error);
  }

  try {
    const session = await requestAuth("/api/auth/register", payload);
    if (session.token && session.user) {
      clearPendingVerification();
      setAuthSession(session);
      await loadRemoteAnalyses();
      showToast(`Selamat datang, ${session.user?.name || "User"}!`, "success");
      return { ok: true, user: state.auth.user };
    }

    setPendingVerification({
      email: session.email,
      verificationId: session.verificationId,
      expiresAt: session.expiresAt,
      devOtp: session.devOtp || "",
      otpSent: Boolean(session.otpSent)
    });
    return { ok: true, verification: state.verification.pending };
  } catch (error) {
    return setAuthError(apiErrorMessage(error, "Registrasi gagal diproses."));
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
    showToast(`Selamat datang, ${session.user?.name || "User"}!`, "success");
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
        return setAuthError(apiErrorMessage(resendError, "Kirim ulang OTP gagal diproses."));
      }
    }

    return setAuthError(apiErrorMessage(error, "Login gagal diproses."));
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
    showToast("Email berhasil diverifikasi!", "success");
    return { ok: true, user: state.auth.user };
  } catch (error) {
    return setVerificationError(apiErrorMessage(error, "Verifikasi OTP gagal diproses."));
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
    return setVerificationError(apiErrorMessage(error, "Kirim ulang OTP gagal diproses."));
  }
}

export async function restoreSession() {
  if (!state.auth.token) {
    return { ok: false };
  }

  try {
    const { data: payload } = await http.get("/api/auth/me");

    setAuthSession({
      user: payload.user,
      token: state.auth.token
    });
    await loadRemoteAnalyses();
    return { ok: true, user: state.auth.user };
  } catch (error) {
    clearAuthSession();
    return { ok: false, error: apiErrorMessage(error, "Sesi login gagal dipulihkan.") };
  }
}

export async function logoutUser() {
  if (state.auth.token) {
    await apiFetch("/api/auth/logout", { method: "POST" }).catch(() => null);
  }

  clearAuthSession();
  clearAccountSettingsMessage();
  showToast("Anda telah keluar dari akun.", "info");
}

export async function updateAccountProfile({ name }) {
  const normalizedName = String(name || "").trim();

  if (normalizedName.length < 2) {
    return setAccountSettingsError("Nama wajib diisi minimal 2 karakter.");
  }

  try {
    const { data: payload } = await http.patch("/api/auth/me", { name: normalizedName });

    setAuthSession({
      user: payload.user,
      token: state.auth.token
    });
    showToast("Profil akun berhasil diperbarui.", "success");
    return setAccountSettingsSuccess("Profil akun berhasil diperbarui.");
  } catch (error) {
    return setAccountSettingsError(apiErrorMessage(error, "Profil gagal diperbarui."));
  }
}

export async function changePassword({ currentPassword, newPassword, confirmPassword }) {
  try {
    await http.post("/api/auth/change-password", { currentPassword, newPassword, confirmPassword });

    showToast("Password berhasil diganti.", "success");
    return setAccountSettingsSuccess("Password berhasil diganti.");
  } catch (error) {
    return setAccountSettingsError(apiErrorMessage(error, "Password gagal diganti."));
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
  const { data } = await http.post(path, payload);
  return data;
}

function apiFetch(path, options = {}) {
  return http.request({ url: path, ...options });
}

async function loadRemoteAnalyses() {
  state.isLoadingHistory = true;
  try {
    const { data: payload } = await apiFetch("/api/analyses");

    replaceAnalyses(Array.isArray(payload.analyses) ? payload.analyses : []);
  } finally {
    state.isLoadingHistory = false;
  }
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

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
