import { getInitialTheme, readStorage, writeStorage } from "./utils.js";

// Bisa diganti lewat localStorage jika service analisis jalan di URL berbeda.
export function getDefaultApiBaseUrl(locationLike = window.location) {
  const hostname = locationLike.hostname;
  const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(hostname);
  return isLocalHost ? "http://127.0.0.1:5000" : locationLike.origin;
}

const defaultApiBaseUrl = getDefaultApiBaseUrl();
export const API_BASE_URL = localStorage.getItem("jobfitApiBaseUrl") || defaultApiBaseUrl;
const AUTH_USER_KEY = "jobfit-auth-user";
const AUTH_TOKEN_KEY = "jobfit-auth-token";
const PENDING_VERIFICATION_KEY = "jobfit-pending-verification";
const ANALYSES_KEY = "jobfit-analyses";
const MAX_STORED_ANALYSES = 30;

function getInitialAuthUser() {
  try {
    const rawUser = window.localStorage.getItem(AUTH_USER_KEY);
    const user = rawUser ? JSON.parse(rawUser) : null;

    if (user?.email && user?.name) {
      return user;
    }
  } catch (error) {
    window.localStorage.removeItem(AUTH_USER_KEY);
  }

  return null;
}

const authUser = getInitialAuthUser();
const authToken = window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
const pendingVerification = readStorage(PENDING_VERIFICATION_KEY, null);

const storedAnalyses = getStoredAnalyses();

// Semua data UI yang berubah saat user memakai aplikasi disimpan di satu tempat.
export const state = {
  // Token session disimpan di browser, data akun dan riwayat disimpan di database.
  auth: {
    user: authUser,
    isAuthenticated: Boolean(authUser),
    token: authToken,
    error: ""
  },

  // State halaman upload.
  selectedFile: null,
  selectedFileUrl: "",
  uploadStep: 1,
  analysisMode: "targeted",
  targetRole: "",
  isAnalyzing: false,
  isLoadingHistory: false,
  loadingStep: 0,
  error: "",
  accountSettings: {
    error: "",
    success: ""
  },
  verification: {
    pending: pendingVerification,
    error: "",
    success: ""
  },

  mobileMenuOpen: false,
  accountMenuOpen: false,
  historyFilters: {
    query: "",
    mode: "all",
    score: "all",
    sort: "newest",
    page: 1
  },
  selectedJobId: "",
  compareAnalysisIds: [],
  theme: getInitialTheme(),
  currentAnalysis: storedAnalyses[0] || null,
  analyses: storedAnalyses,
  history: storedAnalyses.map(toHistoryItem)
};

export function setAuthSession({ user, token }) {
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  state.auth = {
    user,
    token,
    isAuthenticated: true,
    error: ""
  };
}

export function clearAuthSession() {
  window.localStorage.removeItem(AUTH_USER_KEY);
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  state.auth = {
    user: null,
    token: "",
    isAuthenticated: false,
    error: ""
  };
}

export function setPendingVerification(verification) {
  state.verification = {
    pending: verification,
    error: "",
    success: "Kami mengirim kode verifikasi ke email Anda."
  };
  writeStorage(PENDING_VERIFICATION_KEY, verification);
}

export function clearPendingVerification() {
  state.verification = {
    pending: null,
    error: "",
    success: ""
  };
  window.localStorage.removeItem(PENDING_VERIFICATION_KEY);
}

export function setVerificationMessage({ error = "", success = "" }) {
  state.verification = {
    ...state.verification,
    error,
    success
  };
}

export function saveAnalysis(analysis) {
  const normalizedAnalysis = normalizeAnalysis(analysis);
  const nextAnalyses = [
    normalizedAnalysis,
    ...state.analyses.filter((item) => item.id !== normalizedAnalysis.id)
  ].slice(0, MAX_STORED_ANALYSES);

  state.analyses = nextAnalyses;
  state.history = nextAnalyses.map(toHistoryItem);
  state.currentAnalysis = normalizedAnalysis;
  writeStorage(ANALYSES_KEY, nextAnalyses);

  return normalizedAnalysis;
}

export function replaceAnalyses(analyses) {
  const nextAnalyses = Array.isArray(analyses)
    ? analyses.map(normalizeAnalysis).filter((analysis) => analysis.id).slice(0, MAX_STORED_ANALYSES)
    : [];

  state.analyses = nextAnalyses;
  state.history = nextAnalyses.map(toHistoryItem);
  state.currentAnalysis = nextAnalyses[0] || null;
  writeStorage(ANALYSES_KEY, nextAnalyses);
  return nextAnalyses;
}

export function findAnalysisById(id) {
  if (!id) {
    return state.currentAnalysis;
  }

  return state.analyses.find((analysis) => analysis.id === id) || null;
}

function getStoredAnalyses() {
  const stored = readStorage(ANALYSES_KEY, []);
  if (!Array.isArray(stored)) {
    return [];
  }

  return stored
    .filter((analysis) => analysis && typeof analysis === "object")
    .map(normalizeAnalysis)
    .filter((analysis) => analysis.id);
}

function normalizeAnalysis(analysis) {
  return {
    ...analysis,
    id: String(analysis?.id || `analysis-${Date.now()}`),
    targetRole: String(analysis?.targetRole || "Analisis CV"),
    date: String(analysis?.date || new Date().toLocaleDateString("id-ID")),
    score: Number(analysis?.score || 0),
    verdict: String(analysis?.verdict || "Analisis Selesai"),
    summary: String(analysis?.summary || "Analisis CV berhasil diproses."),
    detectedSkills: Array.isArray(analysis?.detectedSkills) ? analysis.detectedSkills : [],
    workExperiences: Array.isArray(analysis?.workExperiences) ? analysis.workExperiences : [],
    totalExperienceYears: Number(analysis?.totalExperienceYears || 0),
    experienceLevel: String(analysis?.experienceLevel || "entry_level"),
    experienceMatch: Number(analysis?.experienceMatch || 0),
    missingSkills: Array.isArray(analysis?.missingSkills) ? analysis.missingSkills : [],
    improvements: Array.isArray(analysis?.improvements) ? analysis.improvements : [],
    jobs: Array.isArray(analysis?.jobs) ? analysis.jobs : [],
    warnings: Array.isArray(analysis?.warnings) ? analysis.warnings : [],
    skillConfidence: analysis?.skillConfidence && typeof analysis.skillConfidence === "object" ? analysis.skillConfidence : {},
    skillMatchTypes: analysis?.skillMatchTypes && typeof analysis.skillMatchTypes === "object" ? analysis.skillMatchTypes : {}
  };
}

function toHistoryItem(analysis) {
  return {
    id: analysis.id,
    date: analysis.date,
    targetRole: analysis.targetRole,
    analysisMode: analysis.analysisMode || "targeted",
    score: Number(analysis.score || 0),
    status: analysis.status || "Selesai"
  };
}
