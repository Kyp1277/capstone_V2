import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml, scoreLabelClass } from "../utils.js";

// Renderer halaman riwayat analisis dari database, dengan cache lokal sebagai fallback.
export function renderHistory() {
  // Rata-rata score dihitung langsung dari data riwayat di memory.
  const avgScore = state.history.length
    ? Math.round(state.history.reduce((sum, item) => sum + item.score, 0) / state.history.length)
    : 0;
  const bestAnalysis = getBestAnalysis();
  const frequentTarget = getFrequentTarget();
  const trend = getScoreTrend();

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
          <p class="summary-label">Analisis terbaik</p>
          <p class="summary-value">${bestAnalysis ? `${bestAnalysis.score}%` : "0%"}</p>
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
          <p class="summary-label">Tren score</p>
          <p class="summary-value">${escapeHtml(trend)}</p>
        </article>
      </div>

      <article class="history-note">
        <strong>${escapeHtml(frequentTarget || "Riwayat tersimpan di database")}</strong>
        <p>${frequentTarget ? "Target ini paling sering muncul di riwayat Anda." : "Hasil analisis terbaru bisa dibuka kembali dari akun yang sama."}</p>
      </article>

      ${renderComparePanel()}

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
  const visible = getVisibleHistory();
  const totalItems = visible.length;
  const totalPages = Math.ceil(totalItems / 10) || 1;

  // Pastikan halaman aktif selalu berada dalam rentang valid
  let page = Math.min(Math.max(Number(state.historyFilters?.page || 1), 1), totalPages);
  if (state.historyFilters && state.historyFilters.page !== page) {
    state.historyFilters.page = page;
  }

  const pageItems = visible.slice((page - 1) * 10, page * 10);

  if (totalItems === 0) {
    return `
      <article class="card dashboard-card" style="text-align: center; padding: 32px;">
        <h3>Tidak ada hasil yang cocok</h3>
        <p>Tidak ada riwayat analisis yang cocok dengan filter atau pencarian Anda. Bersihkan pencarian/filter untuk melihat data kembali.</p>
      </article>
    `;
  }

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
          ${pageItems.map(historyRow).join("")}
        </tbody>
      </table>
    </div>

    <div class="history-cards">
      ${pageItems.map(historyCard).join("")}
    </div>

    ${totalPages > 1 ? `
      <div class="pagination-controls" style="display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 28px; margin-bottom: 8px;">
        <button class="btn btn-secondary" type="button" data-action="prev-history-page" ${page === 1 ? "disabled" : ""}>
          Sebelumnya
        </button>
        <span style="font-size: 14px; font-weight: 600; opacity: 0.85;">
          Halaman ${page} dari ${totalPages}
        </span>
        <button class="btn btn-secondary" type="button" data-action="next-history-page" ${page === totalPages ? "disabled" : ""}>
          Selanjutnya
        </button>
      </div>
    ` : ""}
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
  const selected = isCompareSelected(item.id);
  // Baris tabel untuk tampilan desktop.
  return `
    <tr data-history-row data-history-mode="${escapeHtml(item.analysisMode || "")}" data-history-score="${Number(item.score || 0)}">
      <td>${escapeHtml(item.date)}</td>
      <td>${escapeHtml(item.targetRole)}</td>
      <td><span class="score-badge ${scoreLabelClass(item.score)}">${item.score}%</span></td>
      <td><span class="chip success">${escapeHtml(item.status)}</span></td>
      <td>
        <div class="history-actions">
          <a href="#/dashboard/${encodeURIComponent(item.id)}" class="btn btn-secondary">Lihat Detail</a>
          <button class="btn ${selected ? "btn-primary" : "btn-ghost"}" type="button" data-action="toggle-compare" data-analysis-id="${escapeHtml(item.id)}">${selected ? "Dipilih" : "Bandingkan"}</button>
        </div>
      </td>
    </tr>
  `;
}

function historyCard(item) {
  const selected = isCompareSelected(item.id);
  // Card mobile memakai data yang sama dengan tabel.
  return `
    <article class="card dashboard-card" data-history-row data-history-mode="${escapeHtml(item.analysisMode || "")}" data-history-score="${Number(item.score || 0)}">
      <p class="summary-label">${escapeHtml(item.date)}</p>
      <h3>${escapeHtml(item.targetRole)}</h3>
      <div class="chip-row" style="margin-top: 14px;">
        <span class="score-badge ${scoreLabelClass(item.score)}">${item.score}%</span>
        <span class="chip success">${escapeHtml(item.status)}</span>
      </div>
      <div class="history-card-actions">
        <a href="#/dashboard/${encodeURIComponent(item.id)}" class="btn btn-secondary">Lihat Detail</a>
        <button class="btn ${selected ? "btn-primary" : "btn-ghost"}" type="button" data-action="toggle-compare" data-analysis-id="${escapeHtml(item.id)}">${selected ? "Dipilih untuk compare" : "Bandingkan"}</button>
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

function getBestAnalysis() {
  return [...state.history].sort((left, right) => Number(right.score || 0) - Number(left.score || 0))[0] || null;
}

function getFrequentTarget() {
  const counts = new Map();
  state.history.forEach((item) => {
    const target = item.targetRole || "";
    if (!target) {
      return;
    }
    counts.set(target, (counts.get(target) || 0) + 1);
  });

  return [...counts.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] || "";
}

function getScoreTrend() {
  if (state.history.length < 2) {
    return "Belum cukup";
  }

  const [latest, previous] = state.history;
  const delta = Number(latest.score || 0) - Number(previous.score || 0);

  if (delta > 0) {
    return `Naik ${delta}`;
  }
  if (delta < 0) {
    return `Turun ${Math.abs(delta)}`;
  }
  return "Stabil";
}

function renderComparePanel() {
  const ids = Array.isArray(state.compareAnalysisIds) ? state.compareAnalysisIds : [];
  const selected = ids
    .map((id) => state.analyses.find((analysis) => analysis.id === id))
    .filter(Boolean);

  if (!selected.length) {
    return `
      <article class="compare-panel empty">
        <strong>Bandingkan hasil analisis</strong>
        <p>Pilih sampai dua hasil dari tabel untuk melihat perbedaan score, skill, dan rekomendasi utama.</p>
      </article>
    `;
  }

  return `
    <article class="compare-panel">
      <div class="compare-heading">
        <div>
          <strong>Perbandingan cepat</strong>
          <p>${selected.length}/2 hasil dipilih</p>
        </div>
        <button class="btn btn-ghost" type="button" data-action="clear-compare">Reset</button>
      </div>
      <div class="compare-grid">
        ${selected.map(compareCard).join("")}
      </div>
    </article>
  `;
}

function compareCard(analysis) {
  const topJob = Array.isArray(analysis.jobs) ? analysis.jobs[0] : null;
  const skills = Array.isArray(analysis.detectedSkills) ? analysis.detectedSkills.slice(0, 3) : [];

  return `
    <div class="compare-card">
      <span class="summary-label">${escapeHtml(analysis.date)}</span>
      <h3>${escapeHtml(analysis.targetRole)}</h3>
      <strong>${Number(analysis.score || 0)}%</strong>
      <p>${escapeHtml(topJob?.title || "Belum ada top job")}</p>
      <div class="chip-row">
        ${skills.length ? skills.map((skill) => `<span class="mini-chip match">${escapeHtml(skill)}</span>`).join("") : `<span class="mini-chip gap">Skill belum terbaca</span>`}
      </div>
    </div>
  `;
}

function isCompareSelected(id) {
  return Array.isArray(state.compareAnalysisIds) && state.compareAnalysisIds.includes(id);
}
