import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

export function renderAccount() {
  const user = state.auth.user || { name: "User JobFit", email: "-" };
  const avgScore = state.history.length
    ? Math.round(state.history.reduce((sum, item) => sum + item.score, 0) / state.history.length)
    : 0;
  const latestAnalysis = state.history[0];
  const latestDashboardHref = latestAnalysis ? `#/dashboard/${encodeURIComponent(latestAnalysis.id)}` : "#/dashboard";

  return shell(`
    <section class="container account-hero">
      <div>
        <p class="eyebrow">Dashboard User</p>
        <h1>Halo, ${escapeHtml(user.name)}</h1>
        <p>Kelola analisis CV, cek hasil terakhir, dan lanjutkan pencarian pekerjaan yang paling cocok untuk profil Anda.</p>
      </div>
      <div class="account-actions">
        <a href="#/upload" class="btn btn-primary">Analisis CV</a>
        <button class="btn btn-secondary" type="button" data-action="logout">Keluar</button>
      </div>
    </section>

    <section class="container account-layout">
      <div class="account-main">
        <div class="profile-summary">
          <article class="card summary-item">
            <p class="summary-label">Akun</p>
            <p class="summary-value">${escapeHtml(user.name)}</p>
          </article>
          <article class="card summary-item">
            <p class="summary-label">Total analisis</p>
            <p class="summary-value" data-count-to="${state.history.length}">0</p>
          </article>
          <article class="card summary-item">
            <p class="summary-label">Rata-rata score</p>
            <p class="summary-value" data-count-to="${avgScore}">0%</p>
          </article>
          <article class="card summary-item">
            <p class="summary-label">Status</p>
            <p class="summary-value">Aktif</p>
          </article>
        </div>

        <article class="card dashboard-card">
          <h3>Hasil analisis terakhir</h3>
          ${
            latestAnalysis
              ? `
                <div class="account-latest">
                  <div>
                    <p class="summary-label">${escapeHtml(latestAnalysis.date)}</p>
                    <h2>${escapeHtml(latestAnalysis.targetRole)}</h2>
                    <p>Match score terakhir dari riwayat analisis CV Anda.</p>
                  </div>
                  <span class="score-badge">${Number(latestAnalysis.score || 0)}%</span>
                </div>
                <div class="account-card-actions">
                  <a href="${latestDashboardHref}" class="btn btn-secondary">Lihat Detail</a>
                  <a href="#/history" class="btn btn-ghost">Buka Riwayat</a>
                </div>
              `
              : `<div class="inline-empty">Belum ada riwayat analisis. Mulai dari upload CV untuk membuat hasil pertama.</div>`
          }
        </article>
      </div>

      <aside class="card account-panel">
        <h3>Profil akun</h3>
        <div class="account-profile-row">
          <span>Email</span>
          <strong>${escapeHtml(user.email)}</strong>
        </div>
        <div class="account-shortcuts">
          <a href="#/upload" class="btn btn-primary">Analisis CV Baru</a>
          <a href="#/history" class="btn btn-secondary">Riwayat Analisis</a>
          <a href="#/settings" class="btn btn-secondary">Pengaturan Akun</a>
        </div>
      </aside>
    </section>
  `);
}
