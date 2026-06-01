import { bindEvents } from "./events.js";
import { findAnalysisById, state } from "./state.js";
import { renderAccount } from "./pages/account.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderHistory } from "./pages/history.js";
import { renderLanding } from "./pages/landing.js";
import { renderLogin } from "./pages/login.js";
import { renderNotFound } from "./pages/not-found.js";
import { renderRegister } from "./pages/register.js";
import { renderSettings } from "./pages/settings.js";
import { renderUpload } from "./pages/upload.js";
import { renderVerifyOtp } from "./pages/verify-otp.js";
import { initAnimations, syncAnchorScroll, updatePageTitle } from "./utils.js";

const app = document.querySelector("#app");

// Router hash sederhana: URL seperti #/upload menentukan halaman yang dirender.
const routes = {
  "/": renderLanding,
  "/login": renderLogin,
  "/register": renderRegister,
  "/verify-otp": renderVerifyOtp,
  "/account": renderAccount,
  "/settings": renderSettings,
  "/upload": renderUpload,
  "/dashboard": renderDashboard,
  "/history": renderHistory
};

const protectedRoutes = new Set(["/account", "/settings", "/upload", "/dashboard", "/history"]);
const authRoutes = new Set(["/login", "/register", "/verify-otp"]);
const authRequiredMessage = "Silakan masuk terlebih dahulu untuk membuka halaman ini.";

export function navigate(path) {
  // Semua navigasi internal memakai hash agar tetap cocok untuk static hosting.
  window.location.hash = path === "/" ? "#/" : `#${path}`;
}

export function currentPath() {
  // Jika hash kosong, halaman default adalah landing page.
  const hash = window.location.hash.replace("#", "");
  return hash || "/";
}

let lastRenderedHash = "";

export function render() {
  const route = resolveRoute(currentPath().split("#")[0]);
  const path = route.path;

  if (protectedRoutes.has(path) && !state.auth.isAuthenticated) {
    state.auth.error = authRequiredMessage;
    navigate("/login");
    return;
  }

  if (authRoutes.has(path) && state.auth.isAuthenticated) {
    navigate("/account");
    return;
  }

  if (path === "/register" && state.auth.error === authRequiredMessage) {
    state.auth.error = "";
  }

  const renderer = routes[path] || renderNotFound;

  const currentHash = window.location.hash;
  const isSamePath = currentHash === lastRenderedHash;
  lastRenderedHash = currentHash;

  // Renderer mengembalikan HTML string, lalu event dipasang ulang setelah DOM baru masuk.
  app.innerHTML = renderer(route.params);
  bindEvents();
  initAnimations();
  syncAnchorScroll(isSamePath);
  updatePageTitle(getPageTitle(path, route.params));
}

function getPageTitle(path, params) {
  const titles = {
    "/": "",
    "/login": "Masuk",
    "/register": "Daftar",
    "/verify-otp": "Verifikasi Email",
    "/account": "Dashboard",
    "/settings": "Pengaturan Akun",
    "/upload": "Analisis CV",
    "/history": "Riwayat Analisis",
  };

  if (path === "/dashboard") {
    const analysis = findAnalysisById(params?.analysisId);
    return analysis ? `${analysis.targetRole} — Dashboard` : "Dashboard Hasil";
  }

  return titles[path] ?? "Halaman Tidak Ditemukan";
}

function resolveRoute(path) {
  if (path.startsWith("/dashboard/")) {
    return {
      path: "/dashboard",
      params: {
        analysisId: decodeURIComponent(path.replace("/dashboard/", "").trim())
      }
    };
  }

  return {
    path,
    params: {}
  };
}
