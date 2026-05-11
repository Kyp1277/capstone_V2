const app = document.querySelector("#app");

const state = {
  selectedFile: null,
  targetRole: "",
  isAnalyzing: false,
  error: "",
  mobileMenuOpen: false,
  currentAnalysis: {
    id: "analysis-001",
    targetRole: "Frontend Developer",
    date: "11 Mei 2026",
    score: 82,
    verdict: "Kecocokan Tinggi",
    summary:
      "CV Anda sudah kuat untuk posisi Frontend Developer, terutama pada HTML, CSS, JavaScript, React, Git, dan integrasi REST API. Untuk menaikkan match score, tambahkan bukti pengalaman dengan TypeScript, testing, dan deployment project.",
    detectedSkills: ["HTML", "CSS", "JavaScript", "React", "Git", "REST API"],
    missingSkills: ["TypeScript", "Unit Testing", "CI/CD", "Performance Optimization"],
    improvements: [
      "Tambahkan 2-3 project React yang menjelaskan fitur, tech stack, dan dampak pekerjaan.",
      "Ubah deskripsi pengalaman menjadi lebih terukur, misalnya performa, jumlah pengguna, atau waktu pengerjaan.",
      "Lengkapi bagian skill dengan TypeScript, testing, dan deployment jika Anda sudah pernah memakainya.",
      "Letakkan link portfolio, GitHub, atau live demo di bagian atas CV agar mudah ditemukan recruiter."
    ],
    jobs: [
      {
        title: "Frontend Developer",
        company: "Remote friendly role",
        match: 88,
        detail: "Cocok untuk role yang banyak memakai React dan integrasi API."
      },
      {
        title: "Junior Web Developer",
        company: "Startup technology team",
        match: 84,
        detail: "Cocok untuk membangun fitur web end-to-end dengan HTML, CSS, dan JavaScript."
      },
      {
        title: "React Developer",
        company: "Product engineering",
        match: 79,
        detail: "Perlu memperkuat TypeScript dan reusable component pattern."
      },
      {
        title: "UI Engineer Intern",
        company: "Design system team",
        match: 75,
        detail: "Cocok jika CV menonjolkan slicing UI dan responsive layout."
      }
    ]
  },
  history: [
    {
      id: "analysis-001",
      date: "11 Mei 2026",
      targetRole: "Frontend Developer",
      score: 82,
      status: "Selesai"
    },
    {
      id: "analysis-002",
      date: "9 Mei 2026",
      targetRole: "Data Analyst",
      score: 74,
      status: "Selesai"
    },
    {
      id: "analysis-003",
      date: "4 Mei 2026",
      targetRole: "UI/UX Designer",
      score: 69,
      status: "Selesai"
    }
  ]
};

const routes = {
  "/": renderLanding,
  "/upload": renderUpload,
  "/dashboard": renderDashboard,
  "/history": renderHistory
};

function navigate(path) {
  window.location.hash = path === "/" ? "#/" : `#${path}`;
}

function currentPath() {
  const hash = window.location.hash.replace("#", "");
  return hash || "/";
}

function shell(content) {
  return `
    <div class="app-shell">
      ${navbar()}
      <main class="main">${content}</main>
      ${footer()}
    </div>
  `;
}

function navbar() {
  const path = currentPath();
  const links = [
    ["Beranda", "/"],
    ["Fitur", "/#features"],
    ["Cara Kerja", "/#workflow"],
    ["Riwayat", "/history"]
  ];

  return `
    <header class="navbar">
      <div class="container">
        <div class="nav-inner">
          <a href="#/" class="brand" aria-label="JobFit beranda">
            <span class="brand-mark">JF</span>
            <span>JobFit</span>
          </a>
          <nav class="nav-links" aria-label="Navigasi utama">
            ${links
              .map(([label, href]) => {
                const isActive = href === path || (href === "/#features" && path === "/");
                return `<a class="nav-link ${isActive ? "active" : ""}" href="#${href}">${label}</a>`;
              })
              .join("")}
          </nav>
          <div class="nav-actions">
            <a href="#/upload" class="btn btn-primary">Mulai Analisis</a>
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
          <a class="nav-link" href="#/upload">Analisis CV</a>
          <a class="nav-link" href="#/dashboard">Dashboard</a>
          <a class="nav-link" href="#/history">Riwayat</a>
        </nav>
      </div>
    </header>
  `;
}

function footer() {
  return `
    <footer class="footer">
      <div class="container footer-inner">
        <a href="#/" class="brand">
          <span class="brand-mark">JF</span>
          <span>JobFit</span>
        </a>
        <span>AI CV analysis untuk pencari kerja modern.</span>
      </div>
    </footer>
  `;
}

function renderLanding() {
  return shell(`
    <section class="hero">
      <div class="container hero-grid">
        <div>
          <p class="eyebrow">AI Career Assistant</p>
          <h1>Analisis CV Anda, Temukan Pekerjaan yang Paling Cocok</h1>
          <p class="hero-copy">
            JobFit menggunakan AI untuk membaca CV, mendeteksi skill, menghitung match score,
            dan memberikan rekomendasi karier yang relevan dengan target pekerjaan Anda.
          </p>
          <div class="hero-actions">
            <a href="#/upload" class="btn btn-primary">Mulai Analisis CV</a>
            <a href="#/#workflow" class="btn btn-secondary">Lihat Cara Kerja</a>
          </div>
          <div class="hero-metrics">
            <span class="metric-pill"><span class="metric-dot"></span>REST API ready</span>
            <span class="metric-pill"><span class="metric-dot"></span>AI/ML focused</span>
            <span class="metric-pill"><span class="metric-dot"></span>Responsive layout</span>
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
                <p class="mockup-title">Frontend Developer</p>
                <p class="mockup-subtitle">Hasil analisis AI berdasarkan CV dan target role</p>
              </div>
              <div class="score-mini">82%</div>
            </div>
            <div class="mockup-grid">
              <div class="mini-panel">
                <p class="mini-label">Skill terdeteksi</p>
                <div class="chip-row">
                  <span class="chip">React</span>
                  <span class="chip">REST API</span>
                  <span class="chip">Git</span>
                </div>
              </div>
              <div class="mini-panel">
                <p class="mini-label">Missing skills</p>
                <div class="chip-row">
                  <span class="chip warning">TypeScript</span>
                  <span class="chip warning">Testing</span>
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
          <p>Setiap komponen dirancang agar dapat menerima data dinamis dari backend dan model AI.</p>
        </div>
        <div class="feature-grid">
          ${featureCard("AI", "Analisis CV Otomatis", "Upload CV PDF dan biarkan sistem membaca skill, pengalaman, serta pola kata kunci penting.")}
          ${featureCard("MS", "Match Score", "Lihat skor kecocokan 0-100 persen terhadap target pekerjaan yang Anda masukkan.")}
          ${featureCard("SK", "Missing Skills", "Temukan skill yang belum terlihat kuat di CV dan perlu ditingkatkan.")}
          ${featureCard("JB", "Rekomendasi Pekerjaan", "Dapatkan opsi pekerjaan yang relevan berdasarkan skill dan arah karier Anda.")}
        </div>
      </div>
    </section>

    <section class="section" id="workflow">
      <div class="container">
        <div class="section-heading center">
          <h2>Cara kerja JobFit</h2>
          <p>Alurnya sederhana, tetapi cukup realistis untuk aplikasi full-stack berbasis RESTful API.</p>
        </div>
        <div class="steps">
          ${stepCard(1, "Upload CV", "Masukkan file PDF dan target pekerjaan yang ingin Anda lamar.")}
          ${stepCard(2, "AI menganalisis", "Frontend mengirim file ke API, lalu model AI membaca skill dan kecocokan.")}
          ${stepCard(3, "Lihat rekomendasi", "Dashboard menampilkan score, missing skills, dan saran perbaikan CV.")}
        </div>
      </div>
    </section>
  `);
}

function featureCard(icon, title, body) {
  return `
    <article class="card feature-card">
      <div class="icon-box">${icon}</div>
      <h3>${title}</h3>
      <p>${body}</p>
    </article>
  `;
}

function stepCard(number, title, body) {
  return `
    <article class="card step-card">
      <div class="step-number">${number}</div>
      <h3>${title}</h3>
      <p>${body}</p>
    </article>
  `;
}

function renderUpload() {
  const fileSelected = Boolean(state.selectedFile);
  const canAnalyze = fileSelected && state.targetRole.trim().length > 2 && !state.isAnalyzing;
  const buttonText = state.isAnalyzing
    ? `<span class="spinner" aria-hidden="true"></span> Memproses AI`
    : "Analisis Sekarang";

  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Analisis CV Anda</h1>
        <p>Upload CV dalam format PDF, masukkan target pekerjaan, lalu JobFit akan mensimulasikan networking call ke backend AI analyzer.</p>
      </div>
    </section>

    <section class="container upload-layout">
      <div class="card upload-card">
        <label class="dropzone ${state.isAnalyzing ? "drag-over" : ""}" for="cvFile" data-dropzone>
          <input class="hidden-input" id="cvFile" name="cvFile" type="file" accept="application/pdf,.pdf" data-action="select-file" />
          <span class="dropzone-icon">PDF</span>
          <h2>${fileSelected ? "File CV siap dianalisis" : "Tarik file PDF ke sini atau pilih file"}</h2>
          <p>${fileSelected ? "File berhasil dipilih. Anda masih bisa mengganti file sebelum memulai analisis." : "Format didukung: PDF dengan ukuran maksimal 5 MB. Data akan dikirim ke REST API analisis CV."}</p>
        </label>

        <div class="selected-file ${fileSelected ? "visible" : ""}">
          <div class="file-main">
            <span class="file-icon">PDF</span>
            <div>
              <p class="file-name">${fileSelected ? state.selectedFile.name : ""}</p>
              <p class="file-size">${fileSelected ? formatBytes(state.selectedFile.size) : ""}</p>
            </div>
          </div>
          <button class="btn btn-danger" type="button" data-action="remove-file">Hapus File</button>
        </div>

        <div class="form-field">
          <label for="targetRole">Target pekerjaan</label>
          <input
            class="text-input"
            id="targetRole"
            name="targetRole"
            type="text"
            value="${escapeHtml(state.targetRole)}"
            placeholder="Contoh: Frontend Developer"
            data-action="target-input"
          />
          <span class="helper-text">Contoh endpoint implementasi: POST /api/analyses dengan multipart PDF dan targetRole.</span>
        </div>

        <div class="alert alert-info ${!fileSelected && !state.error && !state.isAnalyzing ? "visible" : ""}">
          Pilih CV PDF dan isi target pekerjaan untuk mengaktifkan tombol analisis.
        </div>
        <div class="alert alert-success ${fileSelected && !state.error && !state.isAnalyzing ? "visible" : ""}">
          File berhasil dipilih. Sistem siap melakukan request ke backend.
        </div>
        <div class="alert alert-info ${state.isAnalyzing ? "visible" : ""}">
          AI sedang membaca dokumen, mendeteksi skill, dan mencocokkan CV dengan target pekerjaan.
        </div>
        <div class="alert alert-error ${state.error ? "visible" : ""}">
          ${state.error}
        </div>

        <div class="upload-actions">
          <button class="btn btn-primary" type="button" ${canAnalyze ? "" : "disabled"} data-action="analyze">
            ${buttonText}
          </button>
          ${state.error ? `<button class="btn btn-secondary" type="button" data-action="clear-error">Coba Lagi</button>` : ""}
        </div>
      </div>

      <aside class="card status-panel">
        <h3>Status integrasi API</h3>
        <p>Desain halaman ini sudah menyiapkan state UI untuk sebelum upload, file terpilih, loading, dan error API.</p>
        <div class="status-list">
          <div class="status-item"><span class="status-check">1</span><span>Validasi file PDF dan ukuran maksimal 5 MB di frontend.</span></div>
          <div class="status-item"><span class="status-check">2</span><span>Kirim file dan target role ke RESTful API menggunakan FormData.</span></div>
          <div class="status-item"><span class="status-check">3</span><span>Tampilkan loading saat backend memproses AI/ML analysis.</span></div>
          <div class="status-item"><span class="status-check">4</span><span>Arahkan ke dashboard ketika response analisis berhasil diterima.</span></div>
        </div>
      </aside>
    </section>
  `);
}

function renderDashboard() {
  const data = state.currentAnalysis;
  return shell(`
    <section class="container dashboard-top">
      <div>
        <p class="eyebrow">Dashboard Hasil Analisis</p>
        <h1>${data.targetRole}</h1>
        <p>Analisis terakhir: ${data.date}</p>
      </div>
      <div class="dashboard-actions">
        <a href="#/upload" class="btn btn-primary">Analisis CV Lain</a>
        <a href="#/" class="btn btn-secondary">Kembali ke Beranda</a>
      </div>
    </section>

    <section class="container">
      <article class="card ai-summary">
        <div class="ai-icon">AI</div>
        <div>
          <h2>Ringkasan hasil AI</h2>
          <p>${data.summary}</p>
        </div>
      </article>
    </section>

    <section class="container dashboard-grid">
      <div class="dashboard-column">
        <article class="card dashboard-card score-card">
          <h3>Match Score</h3>
          <div class="score-circle" style="background: radial-gradient(circle at center, #fff 58%, transparent 59%), conic-gradient(var(--success) 0 ${data.score}%, #e2e8f0 ${data.score}% 100%);">
            <span class="score-value">${data.score}%</span>
          </div>
          <span class="score-label">${data.verdict}</span>
          <p>Cocok untuk posisi junior hingga mid-level dengan fokus penguatan pada missing skills.</p>
        </article>

        <article class="card dashboard-card">
          <h3>Skill yang Terdeteksi</h3>
          <p>Skill berikut terbaca dari CV dan dapat ditampilkan langsung dari response API.</p>
          <div class="chip-row" style="margin-top: 16px;">
            ${data.detectedSkills.map((skill) => `<span class="chip">${skill}</span>`).join("")}
          </div>
        </article>

        <article class="card dashboard-card">
          <h3>Missing Skills</h3>
          <p>Skill yang disarankan untuk dilengkapi agar CV lebih relevan.</p>
          <div class="chip-row" style="margin-top: 16px;">
            ${data.missingSkills.map((skill) => `<span class="chip warning">${skill}</span>`).join("")}
          </div>
        </article>
      </div>

      <div class="dashboard-column">
        <article class="card dashboard-card">
          <h3>Rekomendasi Perbaikan CV</h3>
          <ul class="recommendation-list">
            ${data.improvements.map((item) => `<li>${item}</li>`).join("")}
          </ul>
        </article>

        <article class="card dashboard-card">
          <h3>Rekomendasi Pekerjaan</h3>
          <p>Daftar ini cocok untuk data dinamis dari endpoint rekomendasi pekerjaan.</p>
          <div class="job-grid">
            ${data.jobs.map(jobCard).join("")}
          </div>
        </article>
      </div>
    </section>
  `);
}

function jobCard(job) {
  return `
    <article class="job-card">
      <h4>${job.title}</h4>
      <p>${job.company}</p>
      <div class="progress-bar" aria-label="Match ${job.match} persen">
        <div class="progress-fill" style="width: ${job.match}%"></div>
      </div>
      <div class="job-meta" style="margin-top: 12px;">
        <span class="score-badge">${job.match}% match</span>
        <a href="#/dashboard" class="btn btn-ghost">Detail</a>
      </div>
      <p>${job.detail}</p>
    </article>
  `;
}

function renderHistory() {
  const avgScore = Math.round(state.history.reduce((sum, item) => sum + item.score, 0) / state.history.length);

  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Riwayat Analisis</h1>
        <p>Lihat kembali hasil analisis CV yang pernah dilakukan. Halaman ini siap dihubungkan ke database melalui endpoint GET /api/analyses.</p>
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
          <p class="summary-value">${state.history.length}</p>
        </article>
        <article class="card summary-item">
          <p class="summary-label">Rata-rata score</p>
          <p class="summary-value">${avgScore}%</p>
        </article>
        <article class="card summary-item">
          <p class="summary-label">Status</p>
          <p class="summary-value">Aktif</p>
        </article>
      </div>

      <div class="history-toolbar">
        <input class="text-input" type="search" placeholder="Cari target pekerjaan" data-action="history-search" />
        <a href="#/upload" class="btn btn-primary">Analisis Baru</a>
      </div>

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
            ${state.history.map(historyRow).join("")}
          </tbody>
        </table>
      </div>

      <div class="history-cards">
        ${state.history.map(historyCard).join("")}
      </div>
    </section>
  `);
}

function historyRow(item) {
  return `
    <tr data-history-row>
      <td>${item.date}</td>
      <td>${item.targetRole}</td>
      <td><span class="score-badge">${item.score}%</span></td>
      <td><span class="chip success">${item.status}</span></td>
      <td><a href="#/dashboard" class="btn btn-secondary">Lihat Detail</a></td>
    </tr>
  `;
}

function historyCard(item) {
  return `
    <article class="card dashboard-card" data-history-row>
      <p class="summary-label">${item.date}</p>
      <h3>${item.targetRole}</h3>
      <div class="chip-row" style="margin-top: 14px;">
        <span class="score-badge">${item.score}%</span>
        <span class="chip success">${item.status}</span>
      </div>
      <div style="margin-top: 16px;">
        <a href="#/dashboard" class="btn btn-secondary">Lihat Detail</a>
      </div>
    </article>
  `;
}

function renderNotFound() {
  return shell(`
    <section class="container error-page">
      <div class="error-inner">
        <p class="error-code">404</p>
        <h1>Halaman Tidak Ditemukan</h1>
        <p>Halaman yang Anda cari mungkin sudah dipindahkan atau belum tersedia di prototype JobFit.</p>
        <a href="#/" class="btn btn-primary">Kembali ke Beranda</a>
      </div>
    </section>
  `);
}

function render() {
  const path = currentPath().split("#")[0];
  const renderer = routes[path] || renderNotFound;
  app.innerHTML = renderer();
  bindEvents();
  syncAnchorScroll();
}

function bindEvents() {
  document.querySelectorAll("[data-action='toggle-menu']").forEach((button) => {
    button.addEventListener("click", () => {
      state.mobileMenuOpen = !state.mobileMenuOpen;
      render();
    });
  });

  const fileInput = document.querySelector("[data-action='select-file']");
  if (fileInput) {
    fileInput.addEventListener("change", (event) => {
      const file = event.target.files[0];
      handleFile(file);
    });
  }

  const dropzone = document.querySelector("[data-dropzone]");
  if (dropzone) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      const file = event.dataTransfer.files[0];
      handleFile(file);
    });
  }

  document.querySelectorAll("[data-action='remove-file']").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedFile = null;
      state.error = "";
      render();
    });
  });

  const targetInput = document.querySelector("[data-action='target-input']");
  if (targetInput) {
    targetInput.addEventListener("input", (event) => {
      state.targetRole = event.target.value;
      updateAnalyzeButton();
    });
  }

  document.querySelectorAll("[data-action='analyze']").forEach((button) => {
    button.addEventListener("click", analyzeCv);
  });

  document.querySelectorAll("[data-action='clear-error']").forEach((button) => {
    button.addEventListener("click", () => {
      state.error = "";
      render();
    });
  });

  const search = document.querySelector("[data-action='history-search']");
  if (search) {
    search.addEventListener("input", filterHistory);
  }
}

function handleFile(file) {
  state.error = "";

  if (!file) {
    return;
  }

  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  const isSmallEnough = file.size <= 5 * 1024 * 1024;

  if (!isPdf) {
    state.selectedFile = null;
    state.error = "Upload gagal. File harus berformat PDF.";
    render();
    return;
  }

  if (!isSmallEnough) {
    state.selectedFile = null;
    state.error = "Upload gagal. Ukuran file maksimal 5 MB.";
    render();
    return;
  }

  state.selectedFile = file;
  render();
}

function updateAnalyzeButton() {
  const button = document.querySelector("[data-action='analyze']");
  if (!button) {
    return;
  }
  button.disabled = !(state.selectedFile && state.targetRole.trim().length > 2) || state.isAnalyzing;
}

function analyzeCv() {
  if (!state.selectedFile || state.targetRole.trim().length < 3) {
    state.error = "Lengkapi file CV dan target pekerjaan terlebih dahulu.";
    render();
    return;
  }

  state.isAnalyzing = true;
  state.error = "";
  render();

  window.setTimeout(() => {
    const shouldFail = state.targetRole.trim().toLowerCase().includes("error");
    state.isAnalyzing = false;

    if (shouldFail) {
      state.error = "Upload gagal. API analisis sedang bermasalah. Silakan coba lagi.";
      render();
      return;
    }

    state.currentAnalysis = {
      ...state.currentAnalysis,
      targetRole: state.targetRole.trim(),
      date: "11 Mei 2026"
    };

    const newHistory = {
      id: `analysis-${Date.now()}`,
      date: "11 Mei 2026",
      targetRole: state.targetRole.trim(),
      score: state.currentAnalysis.score,
      status: "Selesai"
    };

    state.history = [newHistory, ...state.history.filter((item) => item.targetRole !== newHistory.targetRole)];
    navigate("/dashboard");
  }, 1500);
}

function filterHistory(event) {
  const query = event.target.value.trim().toLowerCase();
  document.querySelectorAll("[data-history-row]").forEach((row) => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query) ? "" : "none";
  });
}

function formatBytes(bytes) {
  if (!bytes) {
    return "0 KB";
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  return `${(kb / 1024).toFixed(2)} MB`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function syncAnchorScroll() {
  const hash = window.location.hash;
  if (hash.includes("#features") || hash.includes("#workflow")) {
    const id = hash.split("#").at(-1);
    window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  } else {
    window.scrollTo({ top: 0 });
  }
}

window.addEventListener("hashchange", () => {
  state.mobileMenuOpen = false;
  render();
});

render();
