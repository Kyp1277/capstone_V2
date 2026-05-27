import { shell } from "../layout.js";
import { findAnalysisById, state } from "../state.js";
import { escapeHtml } from "../utils.js";

// Renderer dashboard hasil analisis dari state.currentAnalysis.
export function renderDashboard(params = {}) {
  const data = findAnalysisById(params.analysisId);

  if (!data) {
    return renderMissingAnalysis(params.analysisId);
  }

  const scoreMessage = getScoreMessage(data.score);
  const analysisMode = getAnalysisModeLabel(data.analysisMode);
  const dashboardHref = `#/dashboard/${encodeURIComponent(data.id)}`;

  return shell(`
    <section class="container dashboard-top">
      <div>
        <p class="eyebrow">Dashboard Hasil Analisis</p>
        <h1>${escapeHtml(data.targetRole)}</h1>
        <p>Analisis terakhir: ${escapeHtml(data.date)}</p>
        ${analysisMode ? `<span class="mode-badge">${analysisMode}</span>` : ""}
      </div>
      <div class="dashboard-actions">
        <a href="#/upload" class="btn btn-primary">Analisis CV Lain</a>
        <a href="#/history" class="btn btn-secondary">Buka Riwayat</a>
        <a href="#/upload" class="btn btn-ghost" data-rerun-target="${escapeHtml(data.targetRole)}">Analisis ulang target ini</a>
      </div>
    </section>

    <section class="container">
      <article class="card ai-summary">
        <div class="ai-icon">AI</div>
        <div>
          <h2>Ringkasan hasil AI</h2>
          <p>${escapeHtml(data.summary)}</p>
        </div>
      </article>
    </section>

    <section class="container dashboard-grid">
      <div class="dashboard-column">
        <article class="card dashboard-card score-card dashboard-score-card">
          <h3>Match Score</h3>
          <div class="score-circle" style="background: radial-gradient(circle at center, var(--score-hole) 58%, transparent 59%), conic-gradient(var(--success) 0 ${data.score}%, var(--border) ${data.score}% 100%);">
            <span class="score-value" data-count-to="${data.score}">0%</span>
          </div>
          <span class="score-label">${data.verdict}</span>
          <p>${scoreMessage}</p>
        </article>

        <article class="card dashboard-card dashboard-skills-card">
          <h3>Skill yang Terdeteksi</h3>
          <p>Skill berikut terbaca dari CV Anda.</p>
          ${renderChipList(data.detectedSkills, "Belum ada skill yang terbaca jelas dari CV. Pastikan PDF berisi teks, bukan scan gambar.")}
        </article>

        <article class="card dashboard-card dashboard-experience-card">
          <h3>Pengalaman Kerja</h3>
          ${renderExperienceSummary(data)}
        </article>

        <article class="card dashboard-card dashboard-missing-card">
          <h3>Missing Skills</h3>
          <p>Skill yang disarankan untuk dilengkapi agar CV lebih relevan.</p>
          ${renderChipList(data.missingSkills, "Tidak ada missing skill utama untuk hasil analisis ini.", "warning")}
        </article>
      </div>

      <div class="dashboard-column">
        <article class="card dashboard-card dashboard-priority-card">
          <h3>Action Plan CV</h3>
          <p>Langkah praktis yang bisa langsung dipakai sebelum mengirim lamaran.</p>
          ${renderActionPlan(data)}
        </article>

        <article class="card dashboard-card dashboard-improvements-card">
          <h3>Rekomendasi Perbaikan CV</h3>
          ${renderRecommendationList(data.improvements)}
        </article>

        <article class="card dashboard-card dashboard-jobs-card">
          <h3>Rekomendasi Pekerjaan</h3>
          <p>Daftar ini dikelompokkan berdasarkan peluang kecocokan dengan CV Anda.</p>
          ${renderJobList(data.jobs, dashboardHref)}
        </article>
      </div>
    </section>
  `);
}

function renderMissingAnalysis(analysisId) {
  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Hasil analisis tidak ditemukan</h1>
        <p>ID ${escapeHtml(analysisId || "-")} belum tersedia di akun Anda. Buka riwayat yang tersedia atau jalankan analisis CV baru.</p>
      </div>
    </section>

    <section class="container">
      <article class="card dashboard-card">
        <h3>Data belum tersedia</h3>
        <p>Riwayat JobFit tersimpan di database akun. Login ulang lalu buka riwayat jika data belum muncul.</p>
        <div class="upload-actions">
          <a href="#/history" class="btn btn-secondary">Buka Riwayat</a>
          <a href="#/upload" class="btn btn-primary">Analisis CV Baru</a>
        </div>
      </article>
    </section>
  `);
}

function getScoreMessage(score) {
  // Pesan berubah berdasarkan rentang score agar insight terasa lebih personal.
  const normalizedScore = Number(score || 0);

  if (normalizedScore >= 80) {
    return "CV sangat relevan dengan target pekerjaan. Fokus berikutnya adalah memperjelas bukti dampak, pencapaian, dan pengalaman paling kuat.";
  }

  if (normalizedScore >= 60) {
    return "CV sudah cukup kuat untuk target pekerjaan ini, tetapi masih ada beberapa missing skills dan konteks pengalaman yang perlu diperjelas.";
  }

  if (normalizedScore >= 40) {
    return "CV memiliki sebagian kecocokan dengan target pekerjaan, namun perlu penguatan pada skill utama, pengalaman relevan, dan kata kunci lowongan.";
  }

  if (normalizedScore >= 20) {
    return "Kecocokan masih rendah. Prioritaskan skill dasar yang diminta lowongan dan tambahkan project atau pengalaman yang langsung relevan.";
  }

  return "CV belum menunjukkan kecocokan yang cukup dengan target pekerjaan. Mulai dari melengkapi skill inti, ringkasan profil, dan pengalaman yang relevan.";
}

function getAnalysisModeLabel(mode) {
  // Label mode hanya tampil jika data analisis menyimpan mode yang dipilih.
  if (mode === "auto") {
    return "Mode otomatis: cari pekerjaan paling cocok";
  }

  if (mode === "targeted") {
    return "Mode targeted: cek target pekerjaan";
  }

  return "";
}

function renderChipList(items, emptyMessage, variant = "") {
  // Dipakai untuk detected skills dan missing skills.
  if (!Array.isArray(items) || items.length === 0) {
    return `<div class="inline-empty">${emptyMessage}</div>`;
  }

  return `
    <div class="chip-row" style="margin-top: 16px;">
      ${items.map((item) => `<span class="chip ${variant}">${escapeHtml(item)}</span>`).join("")}
    </div>
  `;
}

function renderRecommendationList(items) {
  // Menjaga dashboard tetap rapi walaupun belum ada rekomendasi.
  if (!Array.isArray(items) || items.length === 0) {
    return `<div class="inline-empty">Belum ada rekomendasi perbaikan CV untuk hasil analisis ini.</div>`;
  }

  return `
    <ul class="recommendation-list">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderExperienceSummary(data) {
  const experiences = Array.isArray(data.workExperiences) ? data.workExperiences.slice(0, 3) : [];
  const totalYears = Number(data.totalExperienceYears || 0);
  const experienceMatch = Number(data.experienceMatch || 0);
  const level = formatExperienceLevel(data.experienceLevel);

  if (!experiences.length) {
    return `<div class="inline-empty">Belum ada pengalaman kerja terstruktur yang terbaca dari CV.</div>`;
  }

  return `
    <div class="experience-meta">
      <span>${totalYears} tahun</span>
      <span>${escapeHtml(level)}</span>
      <span>${experienceMatch}% match</span>
    </div>
    <ul class="recommendation-list compact-list">
      ${experiences
        .map((item) => {
          const role = item.position || "Posisi tidak terbaca";
          const company = item.company ? ` - ${item.company}` : "";
          const duration = item.duration ? ` (${item.duration})` : "";
          return `<li>${escapeHtml(`${role}${company}${duration}`)}</li>`;
        })
        .join("")}
    </ul>
  `;
}

function formatExperienceLevel(level) {
  const labels = {
    entry_level: "Entry level",
    junior: "Junior",
    mid_level: "Mid level",
    senior: "Senior",
    senior_manager: "Senior manager"
  };

  return labels[level] || "Entry level";
}

function renderPriorityList(data) {
  const missingSkills = Array.isArray(data.missingSkills) ? data.missingSkills.slice(0, 4) : [];
  const improvements = Array.isArray(data.improvements) ? data.improvements.slice(0, 3) : [];
  const priorities = [
    ...missingSkills.map((skill) => `Perkuat atau tonjolkan skill ${skill} di CV.`),
    ...improvements
  ].slice(0, 5);

  if (!priorities.length) {
    return `<div class="inline-empty">Belum ada prioritas perbaikan khusus dari hasil analisis ini.</div>`;
  }

  return `
    <ul class="recommendation-list">
      ${priorities.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderActionPlan(data) {
  const jobs = Array.isArray(data.jobs) ? data.jobs : [];
  const topJob = jobs[0] || {};
  const matched = Array.isArray(topJob.matchedSkills) ? topJob.matchedSkills.slice(0, 3) : [];
  const missing = Array.isArray(topJob.missingSkills) ? topJob.missingSkills.slice(0, 3) : [];
  const improvements = Array.isArray(topJob.improvements) && topJob.improvements.length
    ? topJob.improvements
    : Array.isArray(data.improvements)
      ? data.improvements
      : [];
  const actions = [
    matched.length
      ? `Tonjolkan bukti penggunaan ${matched.join(", ")} pada pengalaman atau project paling relevan.`
      : "Tambahkan bagian skill yang lebih eksplisit agar sistem dan recruiter mudah membaca kemampuan utama.",
    missing.length
      ? `Lengkapi atau pelajari keyword gap: ${missing.join(", ")}.`
      : "Pertahankan struktur CV saat ini dan tambah metrik dampak pekerjaan.",
    ...improvements
  ].slice(0, 5);

  if (!actions.length) {
    return renderPriorityList(data);
  }

  return `
    <ul class="recommendation-list action-list">
      ${actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderJobList(jobs, dashboardHref) {
  // Daftar pekerjaan berasal dari ranking hasil analisis.
  if (!Array.isArray(jobs) || jobs.length === 0) {
    return `<div class="inline-empty">Belum ada rekomendasi pekerjaan yang tersedia untuk hasil analisis ini.</div>`;
  }

  const groups = [
    ["Paling cocok", jobs.filter((job) => Number(job.match || 0) >= 75)],
    ["Masih bisa dikejar", jobs.filter((job) => Number(job.match || 0) >= 50 && Number(job.match || 0) < 75)],
    ["Kurang cocok", jobs.filter((job) => Number(job.match || 0) < 50)]
  ].filter(([, items]) => items.length);

  return groups
    .map(([label, items]) => `
      <section class="job-category">
        <div class="job-category-header">
          <strong>${label}</strong>
          <span>${items.length} rekomendasi</span>
        </div>
        <div class="job-grid">
          ${items.map((job) => jobCard(job, dashboardHref)).join("")}
        </div>
      </section>
    `)
    .join("");
}

function jobCard(job, dashboardHref) {
  // Setiap job card merangkum match score, alasan cocok, gap skill, dan breakdown.
  const matchedSkills = Array.isArray(job.matchedSkills) ? job.matchedSkills.slice(0, 4) : [];
  const missingSkills = Array.isArray(job.missingSkills) ? job.missingSkills.slice(0, 4) : [];
  const breakdown = job.scoreBreakdown || {};

  return `
    <article class="job-card">
      <h4>${escapeHtml(job.title)}</h4>
      <span class="job-fit-label">${escapeHtml(getJobFitLabel(job.match))}</span>
      <div class="progress-bar" aria-label="Match ${Number(job.match || 0)} persen">
        <div class="progress-fill" style="width: ${Number(job.match || 0)}%"></div>
      </div>
      <div class="job-meta" style="margin-top: 12px;">
        <span class="score-badge">${Number(job.match || 0)}% match</span>
        <a href="${dashboardHref}" class="btn btn-ghost">Detail</a>
      </div>
      <div class="job-explanation">
        <strong>Kenapa cocok?</strong>
        <p>${escapeHtml(job.detail || "Belum ada alasan kecocokan untuk pekerjaan ini.")}</p>
      </div>
      ${
        matchedSkills.length
          ? `<div class="job-skill-row">${matchedSkills.map((skill) => `<span class="mini-chip match">${escapeHtml(skill)}</span>`).join("")}</div>`
          : ""
      }
      <div class="job-explanation">
        <strong>Yang perlu ditingkatkan</strong>
        <p>${escapeHtml(job.notFitReason || "Tambahkan detail pengalaman yang lebih spesifik agar analisis lebih akurat.")}</p>
      </div>
      ${
        missingSkills.length
          ? `<div class="job-skill-row">${missingSkills.map((skill) => `<span class="mini-chip gap">${escapeHtml(skill)}</span>`).join("")}</div>`
          : ""
      }
      ${renderScoreBreakdown(breakdown)}
    </article>
  `;
}

function getJobFitLabel(match) {
  const score = Number(match || 0);
  if (score >= 75) {
    return "Paling cocok";
  }
  if (score >= 50) {
    return "Masih bisa dikejar";
  }
  return "Kurang cocok";
}

function renderScoreBreakdown(breakdown) {
  const items = [
    ["Skill match", breakdown.skillMatch],
    ["Semantic similarity", breakdown.semanticMatch],
    ["Role relevance", breakdown.roleMatch],
    ["Context match", breakdown.contextMatch],
    ["Education match", breakdown.educationMatch]
  ].filter(([, value]) => value !== undefined && value !== null);

  if (!items.length) {
    return "";
  }

  return `
    <div class="score-breakdown">
      ${items.map(([label, value]) => `<span>${label} ${Number(value || 0)}%</span>`).join("")}
    </div>
  `;
}
