import { navigate, render } from "./router.js";
import { replaceAnalyses, saveAnalysis, state } from "./state.js";
import { apiErrorMessage, http } from "./http.js";
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

    const { data: payload } = await http.post("/api/analyses", formData);

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
      apiErrorMessage(error, "Analisis gagal diproses. Coba beberapa saat lagi.") ||
      "Analisis gagal diproses. Coba beberapa saat lagi.";
    showToast(state.error, "error");
    render();
  }
}

export async function loadAnalyses() {
  if (!state.auth.token) {
    return [];
  }

  const { data: payload } = await http.get("/api/analyses");

  return replaceAnalyses(Array.isArray(payload.analyses) ? payload.analyses : []);
}

export async function loadAnalysisDetail(id) {
  if (!state.auth.token || !id) {
    return null;
  }

  const { data: payload } = await http.get(`/api/analyses/${encodeURIComponent(id)}`);

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
    roleFamily: payload.roleFamily || "",
    matchConfidence: payload.matchConfidence || "",
    rankingReasons: Array.isArray(payload.rankingReasons) ? payload.rankingReasons : [],
    riskFlags: Array.isArray(payload.riskFlags) ? payload.riskFlags : [],
    targetAvailable: payload.targetAvailable !== false,
    targetAvailabilityReason: payload.targetAvailabilityReason || "",
    suggestedTargetRoles: Array.isArray(payload.suggestedTargetRoles) ? payload.suggestedTargetRoles : [],
    suggestionReason: payload.suggestionReason || "",
    roadmapSteps: Array.isArray(payload.roadmapSteps) ? payload.roadmapSteps : [],
    portfolioProjects: Array.isArray(payload.portfolioProjects) ? payload.portfolioProjects : [],
    cvQualityScore: Number(payload.cvQualityScore || 0),
    cvQualityFindings: Array.isArray(payload.cvQualityFindings) ? payload.cvQualityFindings : [],
    rewriteHints: Array.isArray(payload.rewriteHints) ? payload.rewriteHints : [],
    skillEvidence: payload.skillEvidence && typeof payload.skillEvidence === "object" ? payload.skillEvidence : {},
    evidenceSummary: payload.evidenceSummary && typeof payload.evidenceSummary === "object" ? payload.evidenceSummary : {},
    targetCoreEvidence: payload.targetCoreEvidence && typeof payload.targetCoreEvidence === "object" ? payload.targetCoreEvidence : {},
    evidenceWarnings: Array.isArray(payload.evidenceWarnings) ? payload.evidenceWarnings : [],
    suppressedJobsCount: Number(payload.suppressedJobsCount || 0),
    suppressionReasons: Array.isArray(payload.suppressionReasons) ? payload.suppressionReasons : [],
    benchmarkWarnings: Array.isArray(payload.benchmarkWarnings) ? payload.benchmarkWarnings : [],
    warnings: Array.isArray(payload.warnings) ? payload.warnings : []
  };
}
