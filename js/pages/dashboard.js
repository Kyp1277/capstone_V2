import { shell } from "../layout.js";
import { findAnalysisById, state } from "../state.js";
import { escapeHtml, scoreColor, scoreLabelClass } from "../utils.js";

// Renderer dashboard hasil analisis dari state.currentAnalysis.
export function renderDashboard(params = {}) {
  const data = findAnalysisById(params.analysisId);

  if (!data) {
    return renderMissingAnalysis(params.analysisId);
  }

  const scoreMessage = getScoreMessage(data.score);
  const analysisMode = getAnalysisModeLabel(data.analysisMode);
  const dashboardHref = `#/dashboard/${encodeURIComponent(data.id)}`;
  const topJob = Array.isArray(data.jobs) ? data.jobs[0] : null;
  const targetMismatch = isTargetMismatch(data, topJob);
  const confidence = targetMismatch ? "target belum cocok" : getConfidenceLabel(topJob?.match ?? data.score);
  const topActions = getTopActions(data, targetMismatch ? null : topJob, targetMismatch);
  const headline = getExecutiveHeadline(data, topJob, targetMismatch);

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
        <button class="btn btn-ghost" type="button" data-action="export-pdf">📥 Ekspor Hasil (PDF)</button>
        <a href="#/upload" class="btn btn-ghost" data-rerun-target="${escapeHtml(data.targetRole)}">Analisis ulang target ini</a>
      </div>
    </section>

    <section class="container dashboard-brief">
      <article class="card ai-summary">
        <div class="ai-icon">AI</div>
        <div>
          <h2>Ringkasan hasil AI</h2>
          <p>${escapeHtml(data.summary)}</p>
        </div>
      </article>

      <article class="card executive-summary ${targetMismatch ? "target-mismatch" : ""}">
        <div class="executive-score">
          <span class="summary-label">Verdict</span>
          <strong>${escapeHtml(targetMismatch ? "Target belum cocok" : data.verdict)}</strong>
          <small>${Number(data.score || 0)}% match score</small>
        </div>
        <div class="executive-main">
          <div class="executive-headline">
            <span class="mode-badge">Confidence ${confidence}</span>
            <h2>${escapeHtml(headline.title)}</h2>
            <p>${escapeHtml(headline.description)}</p>
          </div>
          <div class="executive-actions">
            ${topActions.map((item, index) => `
              <div class="executive-action">
                <span>${index + 1}</span>
                <p>${escapeHtml(item)}</p>
              </div>
            `).join("")}
          </div>
        </div>
      </article>

      ${renderWarningPanel(data.warnings)}
    </section>

    <section class="container dashboard-grid">
      <div class="dashboard-column">
        <article class="card dashboard-card score-card dashboard-score-card">
          <h3>Match Score</h3>
          <div class="score-circle" style="background: radial-gradient(circle at center, var(--score-hole) 58%, transparent 59%), conic-gradient(${scoreColor(data.score)} 0 ${data.score}%, var(--border) ${data.score}% 100%);">
            <span class="score-value" data-count-to="${data.score}">0%</span>
          </div>
          <span class="score-label ${scoreLabelClass(data.score)}">${data.verdict}</span>
          <p>${scoreMessage}</p>
          ${renderScoreBars(topJob?.scoreBreakdown)}
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
          ${renderJobList(data.jobs, dashboardHref, data, targetMismatch)}
        </article>
      </div>
    </section>
  `);
}

function isTargetMismatch(data, topJob) {
  const isTargeted = data.analysisMode === "targeted";
  const score = Number(data.score || topJob?.match || 0);
  const roleMatch = Number(topJob?.scoreBreakdown?.roleMatch ?? 0);

  if (!isTargeted) {
    return false;
  }

  if (!topJob) {
    return true;
  }

  return score < 50 || (score < 60 && roleMatch < 50);
}

function getExecutiveHeadline(data, topJob, targetMismatch) {
  if (targetMismatch) {
    return {
      title: `Belum ada match kuat untuk ${data.targetRole || "target ini"}`,
      description: "JobFit menemukan sinyal kecocokan yang masih lemah, jadi lowongan terdekat tidak dipromosikan sebagai rekomendasi utama. Perkuat skill inti, pengalaman, atau ubah target pekerjaan agar hasilnya lebih akurat."
    };
  }

  return {
    title: topJob?.title || data.targetRole || "Hasil analisis CV",
    description: topJob?.detail || "Buka detail rekomendasi pekerjaan untuk melihat alasan kecocokan dan gap utama."
  };
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

function renderWarningPanel(warnings) {
  if (!Array.isArray(warnings) || warnings.length === 0) {
    return "";
  }

  return `
    <article class="warning-panel">
      <strong>Catatan kualitas CV</strong>
      <p>${escapeHtml(warnings[0])}</p>
    </article>
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

function renderJobList(jobs, dashboardHref, data, targetMismatch = false) {
  // Daftar pekerjaan berasal dari ranking hasil analisis.
  if (!Array.isArray(jobs) || jobs.length === 0) {
    return `<div class="inline-empty">Belum ada rekomendasi pekerjaan yang tersedia untuk hasil analisis ini.</div>`;
  }

  if (targetMismatch) {
    return renderTargetMismatchJobs(data, jobs);
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
          ${items.map((job) => jobCard(job, dashboardHref, jobs.indexOf(job))).join("")}
        </div>
      </section>
    `)
    .join("");
}

function renderTargetMismatchJobs(data, jobs) {
  const alternatives = jobs.slice(0, 3);

  return `
    <div class="target-mismatch-panel">
      <strong>Tidak ada rekomendasi yang cukup cocok</strong>
      <p>Score terbaik masih di bawah ambang rekomendasi untuk target ${escapeHtml(data.targetRole || "ini")}. Lowongan terdekat tidak ditampilkan sebagai rekomendasi utama agar hasil tidak menyesatkan.</p>
      ${
        alternatives.length
          ? `<div class="weak-alternatives">
              <span>Alternatif terdekat, bukan rekomendasi utama:</span>
              ${alternatives.map((job) => `
                <div class="weak-alternative">
                  <strong>${escapeHtml(job.title || "Lowongan")}</strong>
                  <small>${Number(job.match || 0)}% match</small>
                </div>
              `).join("")}
            </div>`
          : ""
      }
      <div class="target-mismatch-actions">
        <a href="#/upload" class="btn btn-primary" data-rerun-target="${escapeHtml(data.targetRole || "")}">Analisis ulang target ini</a>
        <a href="#/upload" class="btn btn-secondary">Coba target lain</a>
      </div>
    </div>
  `;
}

function jobCard(job, dashboardHref, index) {
  // Setiap job card merangkum match score, alasan cocok, gap skill, dan breakdown.
  const matchedSkills = Array.isArray(job.matchedSkills) ? job.matchedSkills.slice(0, 4) : [];
  const missingSkills = Array.isArray(job.missingSkills) ? job.missingSkills.slice(0, 4) : [];
  const breakdown = job.scoreBreakdown || {};
  const jobId = getJobId(job, index);
  const isSelected = state.selectedJobId ? state.selectedJobId === jobId : index === 0;

  return `
    <article class="job-card ${isSelected ? "expanded" : ""}">
      <div class="job-card-top">
        <div>
          <h4>${escapeHtml(job.title)}</h4>
          <span class="job-fit-label">${escapeHtml(getJobFitLabel(job.match))}</span>
        </div>
        <button class="job-toggle" type="button" data-action="select-job" data-job-id="${escapeHtml(jobId)}" aria-expanded="${isSelected ? "true" : "false"}">
          ${isSelected ? "Tutup" : "Detail"}
        </button>
      </div>
      <div class="progress-bar" aria-label="Match ${Number(job.match || 0)} persen">
        <div class="progress-fill" style="width: ${Number(job.match || 0)}%; background: ${scoreColor(job.match)}"></div>
      </div>
      <div class="job-meta" style="margin-top: 12px;">
        <span class="score-badge ${scoreLabelClass(job.match)}">${Number(job.match || 0)}% match</span>
        <a href="${dashboardHref}" class="btn btn-ghost">Detail</a>
      </div>
      <div class="job-detail ${isSelected ? "open" : ""}">
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
        ${renderJobActionPlan(job)}
        ${renderScoreBreakdown(breakdown)}
      </div>
    </article>
  `;
}

function getJobId(job, index) {
  return `${index}-${String(job.title || "job").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function renderJobActionPlan(job) {
  const improvements = Array.isArray(job.improvements) ? job.improvements.slice(0, 3) : [];

  if (!improvements.length) {
    return "";
  }

  return `
    <div class="job-action-plan">
      <strong>Action plan</strong>
      <ul>
        ${improvements.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
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

function renderScoreBars(breakdown) {
  const items = [
    ["Skill", breakdown?.skillMatch],
    ["Semantic", breakdown?.semanticMatch],
    ["Role", breakdown?.roleMatch],
    ["Context", breakdown?.contextMatch],
    ["Education", breakdown?.educationMatch]
  ].filter(([, value]) => value !== undefined && value !== null);

  if (!items.length) {
    return "";
  }

  return `
    <div class="radar-chart-container" style="position: relative; width: 100%; max-width: 280px; margin: 20px auto 10px;">
      <canvas id="radarChart" width="280" height="280" style="display: block; width: 100%; height: auto;"></canvas>
    </div>

    <div class="score-bars" style="margin-top: 16px;">
      ${items.map(([label, value]) => `
        <div class="score-bar-row">
          <span>${label}</span>
          <div class="progress-bar"><div class="progress-fill" style="width: ${Number(value || 0)}%"></div></div>
          <strong>${Number(value || 0)}%</strong>
        </div>
      `).join("")}
    </div>
  `;
}

export function drawRadarChart(canvas, breakdown) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;
  const radius = width * 0.30; // Max radius for 100% (scaled down to prevent labels clipping)

  ctx.clearRect(0, 0, width, height);

  const labels = ["Skill", "Semantic", "Role", "Context", "Education"];
  const values = [
    Number(breakdown.skillMatch ?? 0),
    Number(breakdown.semanticMatch ?? 0),
    Number(breakdown.roleMatch ?? 0),
    Number(breakdown.contextMatch ?? 0),
    Number(breakdown.educationMatch ?? 0)
  ];

  const count = labels.length;
  const angleStep = (Math.PI * 2) / count;

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.08)";
  const textColor = isDark ? "#9ca3af" : "#4b5563";
  const primaryColor = isDark ? "rgba(99, 102, 241, 0.85)" : "rgba(79, 70, 229, 0.85)"; // Indigo
  const fillColor = isDark ? "rgba(99, 102, 241, 0.18)" : "rgba(79, 70, 229, 0.12)";
  const labelFont = "bold 11px Inter, system-ui, sans-serif";

  // 1. Draw Concentric Polygons
  const levels = [0.2, 0.4, 0.6, 0.8, 1.0];
  ctx.strokeStyle = gridColor;
  ctx.lineWidth = 1;

  levels.forEach(level => {
    ctx.beginPath();
    for (let i = 0; i < count; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const r = radius * level;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
  });

  // 2. Draw Axis Lines
  ctx.beginPath();
  for (let i = 0; i < count; i++) {
    const angle = i * angleStep - Math.PI / 2;
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
  }
  ctx.stroke();

  // 3. Draw Labels with dynamic alignments to prevent edge clipping
  ctx.font = labelFont;
  ctx.fillStyle = textColor;
  ctx.textBaseline = "middle";

  for (let i = 0; i < count; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const labelRadius = radius + 14;
    const x = cx + Math.cos(angle) * labelRadius;
    const y = cy + Math.sin(angle) * labelRadius;

    const cosVal = Math.cos(angle);
    if (cosVal > 0.1) {
      ctx.textAlign = "left";
    } else if (cosVal < -0.1) {
      ctx.textAlign = "right";
    } else {
      ctx.textAlign = "center";
    }

    ctx.fillText(labels[i], x, y);
  }

  // 4. Draw Score Polygon
  ctx.beginPath();
  for (let i = 0; i < count; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const scoreVal = Math.min(100, Math.max(0, values[i]));
    const r = radius * (scoreVal / 100);
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();

  ctx.fillStyle = fillColor;
  ctx.fill();

  ctx.strokeStyle = primaryColor;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // 5. Draw Vertices Dots
  ctx.fillStyle = primaryColor;
  for (let i = 0; i < count; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const scoreVal = Math.min(100, Math.max(0, values[i]));
    const r = radius * (scoreVal / 100);
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;

    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function getConfidenceLabel(score) {
  const normalized = Number(score || 0);
  if (normalized >= 75) {
    return "tinggi";
  }
  if (normalized >= 50) {
    return "sedang";
  }
  return "perlu diperkuat";
}

function getTopActions(data, topJob, targetMismatch = false) {
  if (targetMismatch) {
    return [
      `Tambahkan pengalaman, project, atau pelatihan yang langsung menyebut target ${data.targetRole || "pekerjaan ini"}.`,
      "Perkuat bagian ringkasan profil dengan kata kunci pekerjaan yang dituju.",
      "Gunakan mode otomatis jika ingin melihat pekerjaan yang paling realistis dari CV saat ini."
    ];
  }

  const jobImprovements = Array.isArray(topJob?.improvements) ? topJob.improvements : [];
  const fallback = Array.isArray(data.improvements) ? data.improvements : [];
  const missingSkills = Array.isArray(data.missingSkills) ? data.missingSkills.slice(0, 2) : [];
  const actions = [
    ...jobImprovements,
    ...missingSkills.map((skill) => `Tonjolkan atau pelajari skill gap: ${skill}.`),
    ...fallback
  ];

  return actions.filter(Boolean).slice(0, 3);
}
