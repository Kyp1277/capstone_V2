import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml, formatBytes } from "../utils.js";

// Renderer halaman upload CV dan pilihan mode analisis.
export function renderUpload() {
  const fileSelected = Boolean(state.selectedFile);
  const isAutoMode = state.analysisMode === "auto";
  const canContinueToReview = fileSelected && (isAutoMode || state.targetRole.trim().length > 2);
  const currentStep = Math.min(Math.max(Number(state.uploadStep || 1), 1), 3);

  if (state.isAnalyzing) {
    return shell(`
      <section class="analysis-loading-section" aria-live="polite" aria-busy="true">
        <div class="container analysis-loading-inner">
          <div class="analysis-loading-logo-wrap">
            <img class="analysis-loading-logo" src="assets/jobfit-logo-mark.png" alt="" width="180" height="142" />
          </div>
          <span class="analysis-loading-spinner" aria-hidden="true"></span>
          <h1>Menganalisis CV Anda</h1>
          <p>JobFit sedang membaca dokumen, mendeteksi skill, dan mencocokkan rekomendasi pekerjaan.</p>
        </div>
      </section>
    `);
  }

  // Tombol aktif hanya saat file sudah dipilih dan target role valid, kecuali mode auto.
  const canAnalyze = canContinueToReview;

  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Analisis CV Anda</h1>
        <p>Ikuti 3 langkah singkat: pilih mode analisis, upload CV, lalu review sebelum JobFit mulai mencocokkan rekomendasi pekerjaan.</p>
      </div>
    </section>

    <section class="container upload-layout">
      <div class="card upload-card">
        ${renderWizardSteps(currentStep)}
        ${renderWizardPanel(currentStep, { fileSelected, isAutoMode, canContinueToReview })}

        <div class="alert alert-info ${!fileSelected && !state.error && !state.isAnalyzing ? "visible" : ""}">
          ${getStepHint(currentStep, isAutoMode)}
        </div>
        <div class="alert alert-success ${fileSelected && !state.error && !state.isAnalyzing ? "visible" : ""}">
          File berhasil dipilih. Lanjutkan ke review untuk memastikan data sudah benar.
        </div>
        <div class="alert alert-info ${state.isAnalyzing ? "visible" : ""}">
          AI sedang membaca dokumen, mendeteksi skill, dan mencocokkan CV dengan target pekerjaan.
        </div>
        <div class="alert alert-error ${state.error ? "visible" : ""}">
          ${state.error}
        </div>

        ${renderWizardActions(currentStep, canAnalyze, canContinueToReview)}
      </div>

      <aside class="card status-panel">
        <h3>Tips agar hasil lebih akurat</h3>
        <p>Gunakan CV yang mudah dibaca agar JobFit bisa mengenali skill, pengalaman, dan target pekerjaan dengan lebih jelas.</p>
        <div class="status-list">
          <div class="status-item"><span class="status-check">1</span><span>Gunakan PDF teks, bukan hasil scan gambar.</span></div>
          <div class="status-item"><span class="status-check">2</span><span>Tulis nama posisi, perusahaan, dan periode kerja dengan jelas.</span></div>
          <div class="status-item"><span class="status-check">3</span><span>Tambahkan skill penting di pengalaman, project, atau ringkasan profil.</span></div>
          <div class="status-item"><span class="status-check">4</span><span>Pilih target pekerjaan yang spesifik jika ingin analisis lebih terarah.</span></div>
        </div>
      </aside>
    </section>
  `);
}

function renderWizardSteps(currentStep) {
  const steps = [
    ["Mode", "Pilih arah analisis"],
    ["CV", "Upload dan target"],
    ["Review", "Cek sebelum kirim"]
  ];

  return `
    <div class="wizard-steps" aria-label="Progress analisis CV">
      ${steps
        .map(([label, description], index) => {
          const step = index + 1;
          const stateClass = step === currentStep ? "active" : step < currentStep ? "done" : "";
          return `
            <div class="wizard-step ${stateClass}">
              <span class="wizard-step-number">${step}</span>
              <div>
                <strong>${label}</strong>
                <small>${description}</small>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderWizardPanel(currentStep, context) {
  if (currentStep === 1) {
    return renderModeStep(context.isAutoMode);
  }

  if (currentStep === 2) {
    return renderCvStep(context);
  }

  return renderReviewStep(context);
}

function renderModeStep(isAutoMode) {
  return `
    <div class="wizard-panel">
      <div class="wizard-panel-heading">
        <span class="step-kicker">Langkah 1</span>
        <h2>Pilih mode analisis</h2>
        <p>Tentukan apakah JobFit mengecek target pekerjaan tertentu atau mencari pekerjaan yang paling cocok otomatis.</p>
      </div>

      <div class="analysis-mode" role="group" aria-label="Mode analisis">
        <button class="mode-option ${!isAutoMode ? "active" : ""}" type="button" data-analysis-mode="targeted">
          Saya punya tujuan job
        </button>
        <button class="mode-option ${isAutoMode ? "active" : ""}" type="button" data-analysis-mode="auto">
          Cari job paling cocok
        </button>
      </div>
      <span class="helper-text">${isAutoMode ? "Sistem akan ranking pekerjaan berdasarkan skill dan konteks CV tanpa target manual." : "Gunakan mode ini jika Anda ingin mengecek kecocokan terhadap pekerjaan tertentu."}</span>
    </div>
  `;
}

function renderCvStep({ fileSelected, isAutoMode }) {
  return `
    <div class="wizard-panel">
      <div class="wizard-panel-heading">
        <span class="step-kicker">Langkah 2</span>
        <h2>${isAutoMode ? "Upload CV untuk dicocokkan otomatis" : "Upload CV dan isi target pekerjaan"}</h2>
        <p>Gunakan PDF teks maksimal 5 MB agar isi CV dapat dibaca dengan lebih akurat.</p>
      </div>

      ${!isAutoMode ? `
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
          <span class="helper-text">Isi minimal 3 karakter agar tombol review aktif.</span>
        </div>
      ` : ""}

      <label class="dropzone ${state.isAnalyzing ? "drag-over" : ""}" for="cvFile" data-dropzone>
        <input class="hidden-input" id="cvFile" name="cvFile" type="file" accept="application/pdf,.pdf" data-action="select-file" />
        <span class="dropzone-icon">PDF</span>
        <h2>${fileSelected ? "File CV siap direview" : "Tarik file PDF ke sini atau pilih file"}</h2>
        <p>${fileSelected ? "File berhasil dipilih. Anda masih bisa mengganti file sebelum memulai analisis." : "Format aktif saat ini: PDF teks dengan ukuran maksimal 5 MB."}</p>
      </label>

      <div class="selected-file ${fileSelected ? "visible" : ""}">
        <div class="file-main">
          <span class="file-icon">PDF</span>
          <div>
            <p class="file-name">${fileSelected ? escapeHtml(state.selectedFile.name) : ""}</p>
            <p class="file-size">${fileSelected ? formatBytes(state.selectedFile.size) : ""}</p>
          </div>
        </div>
        <button class="btn btn-danger" type="button" data-action="remove-file">Hapus File</button>
      </div>
    </div>
  `;
}

function renderReviewStep({ fileSelected, isAutoMode }) {
  const fileName = fileSelected ? state.selectedFile.name : "Belum ada file";
  const fileSize = fileSelected ? formatBytes(state.selectedFile.size) : "-";
  const target = isAutoMode ? "Pekerjaan paling cocok dari CV" : state.targetRole.trim();

  return `
    <div class="wizard-panel">
      <div class="wizard-panel-heading">
        <span class="step-kicker">Langkah 3</span>
        <h2>Review sebelum analisis</h2>
        <p>Pastikan data sudah benar sebelum JobFit memulai analisis.</p>
      </div>

      <div class="review-summary">
        <div class="review-row">
          <span>Mode</span>
          <strong>${isAutoMode ? "Cari job paling cocok" : "Target pekerjaan tertentu"}</strong>
        </div>
        <div class="review-row">
          <span>Target</span>
          <strong>${escapeHtml(target || "-")}</strong>
        </div>
        <div class="review-row">
          <span>File CV</span>
          <strong>${escapeHtml(fileName)}</strong>
        </div>
        <div class="review-row">
          <span>Ukuran file</span>
          <strong>${fileSize}</strong>
        </div>
      </div>
    </div>
  `;
}

function renderWizardActions(currentStep, canAnalyze, canContinueToReview) {
  if (currentStep === 1) {
    return `
      <div class="upload-actions">
        <button class="btn btn-primary" type="button" data-action="next-upload-step">Lanjut Upload CV</button>
        ${state.error ? `<button class="btn btn-secondary" type="button" data-action="clear-error">Coba Lagi</button>` : ""}
      </div>
    `;
  }

  if (currentStep === 2) {
    return `
      <div class="upload-actions">
        <button class="btn btn-secondary" type="button" data-action="prev-upload-step">Kembali</button>
        <button class="btn btn-primary" type="button" ${canContinueToReview ? "" : "disabled"} data-action="next-upload-step">Review Analisis</button>
        ${state.error ? `<button class="btn btn-secondary" type="button" data-action="clear-error">Coba Lagi</button>` : ""}
      </div>
    `;
  }

  return `
    <div class="upload-actions">
      <button class="btn btn-secondary" type="button" data-action="prev-upload-step">Kembali</button>
      <button class="btn btn-primary" type="button" ${canAnalyze ? "" : "disabled"} data-action="analyze">
        Mulai Analisis
      </button>
      ${state.error ? `<button class="btn btn-secondary" type="button" data-action="clear-error">Coba Lagi</button>` : ""}
    </div>
  `;
}

function getStepHint(currentStep, isAutoMode) {
  if (currentStep === 1) {
    return "Pilih mode analisis yang sesuai dengan kebutuhan Anda.";
  }

  if (currentStep === 2) {
    return isAutoMode
      ? "Pilih CV PDF untuk membiarkan sistem mencari pekerjaan paling cocok."
      : "Isi target pekerjaan dan pilih CV PDF untuk lanjut ke review.";
  }

  return "Cek kembali mode, target, dan file sebelum memulai analisis.";
}
