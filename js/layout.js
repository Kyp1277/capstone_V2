import { state } from "./state.js";
import { applyTheme, escapeHtml } from "./utils.js";

// Shell adalah layout umum yang membungkus semua halaman.
export function shell(content) {
  applyTheme(state.theme);
  return `
    <div class="app-shell">
      ${navbar()}
      <main class="main">${content}</main>
      ${footer()}
    </div>
  `;
}

// Shell khusus halaman auth supaya login/register terasa sebagai page terpisah.
export function authShell(content) {
  const isDark = state.theme === "dark";
  applyTheme(state.theme);

  return `
    <div class="auth-shell">
      <header class="auth-topbar">
        <div class="container auth-topbar-inner">
          ${brandLink()}
          <div class="auth-topbar-actions">
            ${themeButton(isDark)}
            <a href="#/" class="btn btn-secondary">Beranda</a>
          </div>
        </div>
      </header>
      <main class="auth-main">${content}</main>
    </div>
  `;
}

function navbar() {
  // Navbar membaca route aktif dari hash untuk memberi class active pada menu.
  const path = currentPath().split("#")[0];
  const isDark = state.theme === "dark";
  const user = state.auth.user;
  const links = state.auth.isAuthenticated
    ? [
        ["Beranda", "/"],
        ["Dashboard", "/account"],
        ["Riwayat", "/history"]
      ]
    : [
        ["Beranda", "/"],
        ["Fitur", "/#features"],
        ["Cara Kerja", "/#workflow"]
      ];

  return `
    <header class="navbar">
      <div class="container">
        <div class="nav-inner">
          ${brandLink()}
          <nav class="nav-links" aria-label="Navigasi utama">
            ${links
              .map(([label, href]) => {
                const isActive = href === path;
                return `<a class="nav-link ${isActive ? "active" : ""}" href="#${href}">${label}</a>`;
              })
              .join("")}
          </nav>
          <div class="nav-actions">
            ${themeButton(isDark)}
            ${state.auth.isAuthenticated ? authenticatedActions(user) : guestActions()}
          </div>
          <button class="mobile-toggle ${state.mobileMenuOpen ? "active" : ""}" type="button" aria-label="Buka menu" aria-expanded="${state.mobileMenuOpen}" data-action="toggle-menu">
            <span class="menu-dot"></span>
            <span class="menu-dot"></span>
            <span class="menu-dot"></span>
            <span class="menu-dot"></span>
          </button>
        </div>
        <nav class="mobile-menu ${state.mobileMenuOpen ? "open" : ""}" aria-label="Navigasi mobile">
          <a class="nav-link" href="#/">Beranda</a>
          ${state.auth.isAuthenticated ? `
            <a class="nav-link" href="#/upload">Analisis CV</a>
            <a class="nav-link" href="#/account">Dashboard</a>
            <a class="nav-link" href="#/history">Riwayat</a>
            <a class="nav-link" href="#/settings">Pengaturan</a>
            <button class="mobile-auth-link" type="button" data-action="logout">Keluar</button>
          ` : `
            <a class="nav-link" href="#/login">Masuk</a>
            <a class="nav-link" href="#/register">Daftar</a>
          `}
          ${themeButton(isDark, "mobile")}
        </nav>
      </div>
    </header>
  `;
}

function guestActions() {
  return `
    <a href="#/login" class="btn btn-secondary">Masuk</a>
    <a href="#/register" class="btn btn-primary">Daftar</a>
  `;
}

function authenticatedActions(user) {
  return `
    <a href="#/upload" class="btn btn-primary">Analisis CV</a>
    <div class="account-menu-wrap">
      <button class="user-pill ${state.accountMenuOpen ? "active" : ""}" type="button" aria-label="Buka menu akun" aria-expanded="${state.accountMenuOpen}" data-action="toggle-account-menu">
        <span class="user-avatar">${escapeHtml(getUserInitials(user?.name))}</span>
        <span class="user-name" title="${escapeHtml(user?.name || "User")}">${escapeHtml(getShortName(user?.name))}</span>
        <span class="user-caret" aria-hidden="true"></span>
      </button>
      <div class="account-menu ${state.accountMenuOpen ? "open" : ""}" data-account-menu>
        <div class="account-menu-header">
          <span class="user-avatar">${escapeHtml(getUserInitials(user?.name))}</span>
          <div>
            <strong title="${escapeHtml(user?.name || "User")}">${escapeHtml(user?.name || "User")}</strong>
            <small title="${escapeHtml(user?.email || "-")}">${escapeHtml(user?.email || "-")}</small>
          </div>
        </div>
        <a href="#/settings" class="account-menu-item">Pengaturan Akun</a>
        <button class="account-menu-item danger" type="button" data-action="logout">Keluar</button>
      </div>
    </div>
  `;
}

function themeButton(isDark, variant = "desktop") {
  // Tombol theme dipakai ulang di desktop navbar dan menu mobile.
  return `
    <button class="theme-toggle ${variant === "mobile" ? "theme-toggle-mobile" : ""}" type="button" data-action="toggle-theme" aria-label="${isDark ? "Aktifkan light mode" : "Aktifkan dark mode"}">
      <span class="theme-toggle-icon" aria-hidden="true"></span>
      <span class="theme-toggle-label">${isDark ? "Light mode" : "Dark mode"}</span>
    </button>
  `;
}

function footer() {
  // Footer global tampil di semua halaman lewat shell().
  return `
    <footer class="footer">
      <div class="container footer-inner">
        ${brandLink()}
        <span>AI CV analysis untuk pencari kerja modern.</span>
      </div>
    </footer>
  `;
}

function brandLink() {
  return `
    <a href="#/" class="brand" aria-label="JobFit beranda">
      <span class="brand-mark" aria-hidden="true">
        <img src="assets/jobfit-logo-mark.png" alt="" width="54" height="42" />
      </span>
      <span>JobFit</span>
    </a>
  `;
}

function currentPath() {
  // Helper lokal agar layout tidak perlu import router dan membuat dependency melingkar.
  const hash = window.location.hash.replace("#", "");
  return hash || "/";
}

function getUserInitials(name) {
  const words = String(name || "User")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() || "")
    .join("") || "U";
}

function getShortName(name) {
  const words = String(name || "User")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  return words.slice(0, 2).join(" ") || "User";
}
