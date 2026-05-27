import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

// Renderer halaman riwayat analisis dari database, dengan cache lokal sebagai fallback.
export function renderHistory() {
  // Rata-rata score dihitung langsung dari data riwayat di memory.
  const avgScore = state.history.length
    ? Math.round(state.history.reduce((sum, item) => sum + item.score, 0) / state.history.length)
    : 0;

  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Riwayat Analisis</h1>
        <p>Riwayat analisis tersimpan di akun Anda, sehingga hasil terbaru tetap bisa dibuka lagi setelah login.</p>
      </div>
    </section>

    <section class="container history-layout">
      <div class="profile-summary">
        <article class="card summary-item">
          <p class="summary-label">Pengguna</p>
          <p class="summary-value">Akun JobFit</p>
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

      <article class="history-note">
        <strong>Riwayat tersimpan di database</strong>
        <p>Hasil analisis terbaru bisa dibuka kembali dari akun yang sama.</p>
      </article>

      <div class="history-toolbar">
        <input class="text-input" type="search" placeholder="Cari target pekerjaan" data-action="history-search" />
        <select class="text-input" data-action="history-mode-filter" aria-label="Filter mode analisis">
          <option value="all">Semua mode</option>
          <option value="targeted">Targeted</option>
          <option value="auto">Otomatis</option>
        </select>
        <select class="text-input" data-action="history-score-filter" aria-label="Filter score">
          <option value="all">Semua score</option>
          <option value="high">Score >= 75</option>
          <option value="medium">Score 50-74</option>
          <option value="low">Score < 50</option>
        </select>
        <select class="text-input" data-action="history-sort" aria-label="Urutkan riwayat">
          <option value="newest">Terbaru</option>
          <option value="score-desc">Score tertinggi</option>
          <option value="score-asc">Score terendah</option>
        </select>
        <a href="#/upload" class="btn btn-primary">Analisis Baru</a>
      </div>

      ${state.history.length ? renderHistoryContent() : renderEmptyHistory()}
    </section>
  `);
}

function renderHistoryContent() {
  return `
    <div class="card table-card">
      <table class="history-table">
        <thead>
          <tr>
            <th>Tanggal</th>
            <th>Target Pekerjaan</th>
            <th>Match Score</th>
            <th>Status</th>
            <th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          ${getVisibleHistory().map(historyRow).join("")}
        </tbody>
      </table>
    </div>

    <div class="history-cards">
      ${getVisibleHistory().map(historyCard).join("")}
    </div>
  `;
}

function renderEmptyHistory() {
  return `
    <article class="card dashboard-card">
      <h3>Belum ada riwayat analisis</h3>
      <p>Upload CV pertama Anda untuk membuat hasil analisis yang bisa dibuka kembali dari halaman ini.</p>
      <div style="margin-top: 16px;">
        <a href="#/upload" class="btn btn-primary">Mulai Analisis</a>
      </div>
    </article>
  `;
}

function historyRow(item) {
  // Baris tabel untuk tampilan desktop.
  return `
    <tr data-history-row data-history-mode="${escapeHtml(item.analysisMode || "")}" data-history-score="${Number(item.score || 0)}">
      <td>${escapeHtml(item.date)}</td>
      <td>${escapeHtml(item.targetRole)}</td>
      <td><span class="score-badge">${item.score}%</span></td>
      <td><span class="chip success">${escapeHtml(item.status)}</span></td>
      <td><a href="#/dashboard/${encodeURIComponent(item.id)}" class="btn btn-secondary">Lihat Detail</a></td>
    </tr>
  `;
}

function historyCard(item) {
  // Card mobile memakai data yang sama dengan tabel.
  return `
    <article class="card dashboard-card" data-history-row data-history-mode="${escapeHtml(item.analysisMode || "")}" data-history-score="${Number(item.score || 0)}">
      <p class="summary-label">${escapeHtml(item.date)}</p>
      <h3>${escapeHtml(item.targetRole)}</h3>
      <div class="chip-row" style="margin-top: 14px;">
        <span class="score-badge">${item.score}%</span>
        <span class="chip success">${escapeHtml(item.status)}</span>
      </div>
      <div style="margin-top: 16px;">
        <a href="#/dashboard/${encodeURIComponent(item.id)}" class="btn btn-secondary">Lihat Detail</a>
      </div>
    </article>
  `;
}

function getVisibleHistory() {
  const items = [...state.history];
  const sortMode = state.historyFilters?.sort || "newest";

  if (sortMode === "score-desc") {
    items.sort((left, right) => Number(right.score || 0) - Number(left.score || 0));
  } else if (sortMode === "score-asc") {
    items.sort((left, right) => Number(left.score || 0) - Number(right.score || 0));
  }

  return items.filter((item) => {
    const query = String(state.historyFilters?.query || "").trim().toLowerCase();
    const mode = state.historyFilters?.mode || "all";
    const scoreFilter = state.historyFilters?.score || "all";
    const score = Number(item.score || 0);
    const searchable = `${item.date} ${item.targetRole} ${item.status} ${item.analysisMode || ""}`.toLowerCase();

    if (query && !searchable.includes(query)) {
      return false;
    }
    if (mode !== "all" && item.analysisMode !== mode) {
      return false;
    }
    if (scoreFilter === "high" && score < 75) {
      return false;
    }
    if (scoreFilter === "medium" && (score < 50 || score >= 75)) {
      return false;
    }
    if (scoreFilter === "low" && score >= 50) {
      return false;
    }

    return true;
  });
}
