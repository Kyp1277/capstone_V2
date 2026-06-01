import { navigate, render } from "./router.js";
import { API_BASE_URL, replaceAnalyses, saveAnalysis, state } from "./state.js";
import { showToast } from "./utils.js";

// Mengirim CV untuk dianalisis dan mengubah response menjadi data dashboard.
export async function analyzeCv() {
  const isAutoMode = state.analysisMode === "auto";
  if (!state.selectedFile || (!isAutoMode && state.targetRole.trim().length < 3)) {
    state.error = isAutoMode
      ? "Pilih file CV terlebih dahulu."
      : "Lengkapi file CV dan target pekerjaan terlebih dahulu.";
    render();
    return;
  }

  state.isAnalyzing = true;
  state.loadingStep = 1;
  state.error = "";

  render();
  const loadingTimer = window.setInterval(() => {
    if (!state.isAnalyzing) {
      window.clearInterval(loadingTimer);
      return;
    }
    state.loadingStep = Math.min(Number(state.loadingStep || 1) + 1, 4);
    render();
  }, 1100);

  try {
    // Request berisi file PDF, mode analisis, dan target role.
    const formData = new FormData();
    formData.append("cv", state.selectedFile);
    formData.append("analysisMode", state.analysisMode);
    formData.append("targetRole", isAutoMode ? "Pekerjaan paling cocok dari CV" : state.targetRole.trim());

    const response = await fetch(`${API_BASE_URL}/api/analyses`, {
      method: "POST",
      headers: authHeaders(),
      body: formData
    });

    const payload = await response.json().catch(() => ({}));

    // Response non-2xx tetap dibaca agar pesan validasi bisa tampil.
    if (!response.ok) {
      throw new Error(getApiErrorMessage(payload));
    }

    const analysis = normalizeAnalysisResponse(payload);
    const savedAnalysis = saveAnalysis(analysis);
    if (state.selectedFileUrl) {
      URL.revokeObjectURL(state.selectedFileUrl);
      state.selectedFileUrl = "";
    }
    state.isAnalyzing = false;
    state.loadingStep = 0;
    state.selectedFile = null;
    state.targetRole = "";
    state.uploadStep = 1;
    state.selectedJobId = "";
    window.clearInterval(loadingTimer);
    showToast("Analisis CV selesai! Membuka dashboard...", "success");
    navigate(`/dashboard/${savedAnalysis.id}`);
  } catch (error) {
    state.isAnalyzing = false;
    state.loadingStep = 0;
    window.clearInterval(loadingTimer);
    state.error =
      error.message ||
      "Analisis gagal diproses. Coba beberapa saat lagi.";
    showToast(state.error, "error");
    render();
  }
}

export async function loadAnalyses() {
  if (!state.auth.token) {
    return [];
  }

  const response = await fetch(`${API_BASE_URL}/api/analyses`, {
    headers: authHeaders()
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload));
  }

  return replaceAnalyses(Array.isArray(payload.analyses) ? payload.analyses : []);
}

export async function loadAnalysisDetail(id) {
  if (!state.auth.token || !id) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/analyses/${encodeURIComponent(id)}`, {
    headers: authHeaders()
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload));
  }

  return saveAnalysis(normalizeAnalysisResponse(payload));
}

function normalizeAnalysisResponse(payload) {
  // Normalisasi menjaga dashboard tetap aman walaupun ada field response yang kosong.
  return {
    ...(state.currentAnalysis || {}),
    id: payload.id || `analysis-${Date.now()}`,
    targetRole: payload.targetRole || state.targetRole.trim() || "Analisis CV",
    date: payload.date || new Date().toLocaleDateString("id-ID", {
      day: "numeric",
      month: "long",
      year: "numeric"
    }),
    score: Number(payload.score || 0),
    analysisMode: payload.analysisMode || state.analysisMode,
    verdict: payload.verdict || "Analisis Selesai",
    summary: payload.summary || "Analisis CV berhasil diproses.",
    detectedSkills: Array.isArray(payload.detectedSkills) ? payload.detectedSkills : [],
    workExperiences: Array.isArray(payload.workExperiences) ? payload.workExperiences : [],
    totalExperienceYears: Number(payload.totalExperienceYears || 0),
    experienceLevel: payload.experienceLevel || "entry_level",
    experienceMatch: Number(payload.experienceMatch || 0),
    missingSkills: Array.isArray(payload.missingSkills) ? payload.missingSkills : [],
    improvements: Array.isArray(payload.improvements) ? payload.improvements : [],
    jobs: Array.isArray(payload.jobs) ? payload.jobs : [],
    warnings: Array.isArray(payload.warnings) ? payload.warnings : []
  };
}

function authHeaders() {
  return state.auth.token ? { Authorization: `Bearer ${state.auth.token}` } : {};
}

function getApiErrorMessage(payload) {
  // Service analisis bisa mengirim detail error sebagai string atau array validasi.
  const detail = payload?.detail || payload?.error;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        const message = item.msg || "Validasi request gagal.";
        return location ? `${location}: ${message}` : message;
      })
      .join(" ");
  }

  return "Analisis sedang bermasalah. Coba beberapa saat lagi.";
}
