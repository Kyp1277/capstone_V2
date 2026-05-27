import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

// Renderer landing page: hero, fitur utama, dan workflow.
export function renderLanding() {
  const latestAnalysis = state.analyses[0] || null;
  const hasAnalysis = Boolean(latestAnalysis?.id);
  const topJob = Array.isArray(latestAnalysis?.jobs) ? latestAnalysis.jobs[0] : null;
  const mockupTitle = hasAnalysis
    ? topJob?.title || latestAnalysis.targetRole || "Hasil analisis CV"
    : "Belum ada analisis";
  const mockupSubtitle = hasAnalysis
    ? `Hasil terbaru: ${latestAnalysis.targetRole || "Analisis CV"}`
    : "Upload CV untuk menampilkan hasil riwayat asli";
  const mockupScore = hasAnalysis ? Number(topJob?.match || latestAnalysis.score || 0) : 0;
  const detectedSkills = hasAnalysis ? safeList(latestAnalysis.detectedSkills).slice(0, 3) : [];
  const missingSkills = hasAnalysis ? safeList(latestAnalysis.missingSkills).slice(0, 2) : [];

  return shell(`
    <section class="hero">
      <div class="container hero-grid">
        <div>
          <p class="eyebrow">AI Career Assistant</p>
          <h1>Analisis CV Anda, Temukan Pekerjaan yang Paling Cocok</h1>
          <p class="hero-copy">
            JobFit membaca CV PDF, mengenali skill dan pengalaman, menghitung match score,
            menemukan missing skills, dan menyusun rekomendasi pekerjaan yang relevan.
          </p>
          <div class="hero-actions">
            <a href="#/upload" class="btn btn-primary">Mulai Analisis CV</a>
            <a href="#/#workflow" class="btn btn-secondary">Lihat Cara Kerja</a>
          </div>
          <div class="hero-metrics">
            <span class="metric-pill"><span class="metric-dot"></span>CV parsing</span>
            <span class="metric-pill"><span class="metric-dot"></span>NLP skill extraction</span>
            <span class="metric-pill"><span class="metric-dot"></span>Rekomendasi pekerjaan</span>
          </div>
        </div>

        <aside class="mockup-frame" aria-label="Mockup dashboard hasil JobFit">
          <div class="mockup-top">
            <span class="window-dot"></span>
            <span class="window-dot"></span>
            <span class="window-dot"></span>
          </div>
          <div class="mockup-card">
            <div class="mockup-header">
              <div>
                <p class="mockup-title">${escapeHtml(mockupTitle)}</p>
                <p class="mockup-subtitle">${escapeHtml(mockupSubtitle)}</p>
              </div>
              <div class="score-mini" data-count-to="${mockupScore}">0%</div>
            </div>
            <div class="mockup-grid">
              <div class="mini-panel">
                <p class="mini-label">Skill terdeteksi</p>
                <div class="chip-row">
                  ${renderMiniChips(detectedSkills, "Belum ada skill")}
                </div>
              </div>
              <div class="mini-panel">
                <p class="mini-label">Missing skills</p>
                <div class="chip-row">
                  ${renderMiniChips(missingSkills, "Belum ada gap", "warning")}
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section class="section" id="features">
      <div class="container">
        <div class="section-heading">
          <h2>Fitur utama untuk memahami potensi CV Anda</h2>
          <p>JobFit membantu memahami kekuatan CV, celah skill, dan peluang pekerjaan yang paling relevan.</p>
        </div>
        <div class="feature-grid">
          ${featureCard("CV", "CV Parsing", "Upload CV PDF lalu JobFit membaca isi dokumen untuk dianalisis.")}
          ${featureCard("NLP", "Skill Extraction", "Sistem membaca skill dari CV dan deskripsi pekerjaan dengan normalisasi sinonim.")}
          ${featureCard("MS", "Match Score & Gap", "Lihat skor kecocokan 0-100 persen, skill yang terdeteksi, dan missing skills utama.")}
          ${featureCard("JB", "Rekomendasi", "Dapatkan saran perbaikan CV dan rekomendasi pekerjaan berdasarkan hasil analisis.")}
        </div>
      </div>
    </section>

    <section class="section" id="workflow">
      <div class="container">
        <div class="section-heading center">
          <h2>Cara kerja JobFit</h2>
          <p>Mulai dari upload CV sampai rekomendasi pekerjaan, semuanya dirancang agar cepat dan mudah diikuti.</p>
        </div>
        <div class="steps">
          ${stepCard(1, "Upload CV", "Masukkan file PDF dan pilih mode targeted atau auto recommendation.")}
          ${stepCard(2, "JobFit menganalisis", "Sistem membaca isi CV, mendeteksi skill, menghitung kecocokan, dan mencari gap utama.")}
          ${stepCard(3, "Lihat rekomendasi", "Dashboard menampilkan score, missing skills, saran perbaikan CV, dan rekomendasi pekerjaan.")}
        </div>
      </div>
    </section>
  `);
}

function safeList(items) {
  return Array.isArray(items) ? items.filter(Boolean) : [];
}

function renderMiniChips(items, emptyLabel, variant = "") {
  if (!items.length) {
    return `<span class="chip ${variant}">${emptyLabel}</span>`;
  }

  return items
    .map((item) => `<span class="chip ${variant}">${escapeHtml(item)}</span>`)
    .join("");
}

function featureCard(icon, title, body) {
  // Helper kecil agar markup kartu fitur tidak ditulis berulang.
  return `
    <article class="card feature-card">
      <div class="icon-box">${icon}</div>
      <h3>${title}</h3>
      <p>${body}</p>
    </article>
  `;
}

function stepCard(number, title, body) {
  // Helper untuk kartu langkah pada section cara kerja.
  return `
    <article class="card step-card">
      <div class="step-number">${number}</div>
      <h3>${title}</h3>
      <p>${body}</p>
    </article>
  `;
}
