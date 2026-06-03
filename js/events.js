import {
  changePassword,
  clearAccountSettingsMessage,
  clearAuthError,
  clearVerificationMessage,
  loginUser,
  logoutUser,
  registerUser,
  resendOtp,
  updateAccountProfile,
  verifyOtp
} from "./auth.js";
import { analyzeCv } from "./api.js";
import { navigate, render } from "./router.js";
import { findAnalysisById, state } from "./state.js";
import { http } from "./http.js";
import { applyTheme, debounce, escapeHtml } from "./utils.js";
import { drawRadarChart } from "./pages/dashboard.js";

// Render yang di-debounce khusus untuk input pencarian riwayat.
const debouncedRender = debounce(() => render(), 300);

// Fetch autocomplete suggestions untuk target pekerjaan
const debouncedFetchSuggestions = debounce(async (query) => {
  const datalist = document.getElementById("targetRoleSuggestions");
  if (!datalist) return;

  if (query.trim().length < 2) {
    datalist.innerHTML = "";
    return;
  }

  try {
    const { data } = await http.get("/api/analyses/titles", {
      params: { q: query }
    });
    datalist.innerHTML = (data.titles || [])
      .map((title) => `<option value="${escapeHtml(title)}"></option>`)
      .join("");
  } catch (err) {
    console.error("Gagal mengambil saran autocomplete target role", err);
  }
}, 250);

// Setelah setiap render, DOM baru perlu dipasangi event listener lagi.
export function bindEvents() {
  document.querySelectorAll("[data-action='toggle-theme']").forEach((button) => {
    button.addEventListener("click", () => {
      state.theme = state.theme === "dark" ? "light" : "dark";
      window.localStorage.setItem("jobfit-theme", state.theme);
      applyTheme(state.theme);
      render();
    });
  });

  document.querySelectorAll("[data-action='toggle-menu']").forEach((button) => {
    button.addEventListener("click", () => {
      state.mobileMenuOpen = !state.mobileMenuOpen;
      state.accountMenuOpen = false;
      render();
    });
  });

  document.querySelectorAll("[data-action='toggle-account-menu']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      state.accountMenuOpen = !state.accountMenuOpen;
      state.mobileMenuOpen = false;
      render();
    });
  });

  if (state.accountMenuOpen) {
    document.addEventListener(
      "click",
      (event) => {
        if (!event.target.closest(".account-menu-wrap")) {
          state.accountMenuOpen = false;
          render();
        }
      },
      { once: true }
    );
  }

  document.querySelectorAll("[data-action='logout']").forEach((button) => {
    button.addEventListener("click", async () => {
      state.accountMenuOpen = false;
      state.mobileMenuOpen = false;
      await logoutUser();
      navigate("/login");
    });
  });

  bindAuthForms();
  bindOtpForm();
  bindAccountSettingsForms();

  document.querySelectorAll("[data-analysis-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      // Mode auto menyembunyikan input target role, targeted menampilkannya kembali.
      state.analysisMode = button.dataset.analysisMode;
      state.error = "";
      render();
    });
  });

  document.querySelectorAll("[data-action='next-upload-step']").forEach((button) => {
    button.addEventListener("click", () => {
      if (state.uploadStep === 2 && !canReviewUpload()) {
        state.error =
          state.analysisMode === "auto"
            ? "Pilih file CV terlebih dahulu."
            : "Isi target pekerjaan dan pilih file CV terlebih dahulu.";
        render();
        return;
      }

      state.error = "";
      state.uploadStep = Math.min(Number(state.uploadStep || 1) + 1, 3);
      render();
    });
  });

  document.querySelectorAll("[data-action='prev-upload-step']").forEach((button) => {
    button.addEventListener("click", () => {
      state.error = "";
      state.uploadStep = Math.max(Number(state.uploadStep || 1) - 1, 1);
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

  bindDropzone();

  document.querySelectorAll("[data-action='remove-file']").forEach((button) => {
    button.addEventListener("click", () => {
      if (state.selectedFileUrl) {
        URL.revokeObjectURL(state.selectedFileUrl);
        state.selectedFileUrl = "";
      }
      state.selectedFile = null;
      state.error = "";
      render();
    });
  });

  const targetInput = document.querySelector("[data-action='target-input']");
  if (targetInput) {
    targetInput.addEventListener("input", (event) => {
      // Input target role disimpan di state tanpa render ulang agar mengetik tetap halus.
      state.targetRole = event.target.value;
      updateAnalyzeButton();
      debouncedFetchSuggestions(event.target.value);
    });
  }

  document.querySelectorAll("[data-action='analyze']").forEach((button) => {
    button.addEventListener("click", analyzeCv);
  });

  document.querySelectorAll("[data-action='select-job']").forEach((button) => {
    button.addEventListener("click", () => {
      const jobId = button.dataset.jobId || "";
      const isExpanded = button.getAttribute("aria-expanded") === "true";
      state.selectedJobId = isExpanded ? "__closed" : jobId;
      render();
    });
  });

  document.querySelectorAll("[data-action='clear-error']").forEach((button) => {
    button.addEventListener("click", () => {
      state.error = "";
      render();
    });
  });

  const search = document.querySelector("[data-action='history-search']");
  if (search) {
    search.addEventListener("input", (event) => {
      state.historyFilters.query = event.target.value;
      state.historyFilters.page = 1;
      debouncedRender();
    });
  }

  const historyMode = document.querySelector("[data-action='history-mode-filter']");
  if (historyMode) {
    historyMode.value = state.historyFilters.mode;
    historyMode.addEventListener("change", (event) => {
      state.historyFilters.mode = event.target.value;
      state.historyFilters.page = 1;
      render();
    });
  }

  const historyScore = document.querySelector("[data-action='history-score-filter']");
  if (historyScore) {
    historyScore.value = state.historyFilters.score;
    historyScore.addEventListener("change", (event) => {
      state.historyFilters.score = event.target.value;
      state.historyFilters.page = 1;
      render();
    });
  }

  const historySort = document.querySelector("[data-action='history-sort']");
  if (historySort) {
    historySort.value = state.historyFilters.sort;
    historySort.addEventListener("change", (event) => {
      state.historyFilters.sort = event.target.value;
      state.historyFilters.page = 1;
      render();
    });
  }

  document.querySelectorAll("[data-action='prev-history-page']").forEach((button) => {
    button.addEventListener("click", () => {
      state.historyFilters.page = Math.max((state.historyFilters.page || 1) - 1, 1);
      render();
    });
  });

  document.querySelectorAll("[data-action='next-history-page']").forEach((button) => {
    button.addEventListener("click", () => {
      state.historyFilters.page = (state.historyFilters.page || 1) + 1;
      render();
    });
  });

  document.querySelectorAll("[data-action='toggle-compare']").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.analysisId || "";
      const current = Array.isArray(state.compareAnalysisIds) ? state.compareAnalysisIds : [];
      state.compareAnalysisIds = current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id].slice(-2);
      render();
    });
  });

  document.querySelectorAll("[data-action='clear-compare']").forEach((button) => {
    button.addEventListener("click", () => {
      state.compareAnalysisIds = [];
      render();
    });
  });

  document.querySelectorAll("[data-rerun-target]").forEach((link) => {
    link.addEventListener("click", () => {
      const target = link.dataset.rerunTarget || "";
      state.analysisMode = "targeted";
      state.targetRole = target;
      state.uploadStep = 2;
      state.error = "";
    });
  });

  document.querySelectorAll("[data-action='export-pdf']").forEach((button) => {
    button.addEventListener("click", () => {
      window.print();
    });
  });

  document.querySelectorAll("[data-action='toggle-password']").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        button.innerHTML = "🙈";
        button.setAttribute("aria-label", "Sembunyikan password");
      } else {
        input.type = "password";
        button.innerHTML = "👁️";
        button.setAttribute("aria-label", "Tampilkan password");
      }
    });
  });

  // Gambar Radar Chart jika elemen kanvas tersedia di DOM
  const canvas = document.getElementById("radarChart");
  if (canvas) {
    const activeRouteParams = window.location.hash.split("/");
    const analysisId = activeRouteParams[2] ? decodeURIComponent(activeRouteParams[2]) : "";
    const analysis = findAnalysisById(analysisId);

    const topJob = analysis?.jobs?.[0];
    const breakdown = topJob?.scoreBreakdown || {
      skillMatch: Number(analysis?.score || 50),
      semanticMatch: Number(analysis?.score || 50),
      roleMatch: Number(analysis?.score || 50),
      contextMatch: Number(analysis?.score || 50),
      educationMatch: Number(analysis?.score || 50)
    };
    drawRadarChart(canvas, breakdown);
  }
}

function bindAuthForms() {
  const loginForm = document.querySelector("[data-auth-form='login']");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(loginForm);
      const result = await loginUser({
        email: formData.get("email"),
        password: formData.get("password")
      });

      if (result.ok) {
        navigate("/account");
      } else if (result.needsVerification) {
        navigate("/verify-otp");
      } else {
        render();
      }
    });
  }

  const registerForm = document.querySelector("[data-auth-form='register']");
  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(registerForm);
      const result = await registerUser({
        name: formData.get("name"),
        email: formData.get("email"),
        password: formData.get("password")
      });

      if (result.ok) {
        navigate("/verify-otp");
      } else {
        render();
      }
    });
  }

  document.querySelectorAll("[data-auth-form] input").forEach((input) => {
    input.addEventListener("input", () => {
      if (state.auth.error) {
        clearAuthError();
        const alert = input.closest("form")?.querySelector(".alert-error");
        if (alert) {
          alert.classList.remove("visible");
          alert.textContent = "";
        }
      }
      if (state.verification.error || state.verification.success) {
        clearVerificationMessage();
      }
    });
  });
}

function bindOtpForm() {
  const otpForm = document.querySelector("[data-auth-form='verify-otp']");
  if (otpForm) {
    otpForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(otpForm);
      const result = await verifyOtp({
        otp: formData.get("otp")
      });

      if (result.ok) {
        navigate("/account");
      } else {
        render();
      }
    });
  }

  document.querySelectorAll("[data-action='resend-otp']").forEach((button) => {
    button.addEventListener("click", async () => {
      await resendOtp();
      render();
    });
  });
}

function bindAccountSettingsForms() {
  const profileForm = document.querySelector("[data-account-form='profile']");
  if (profileForm) {
    profileForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(profileForm);
      await updateAccountProfile({
        name: formData.get("name")
      });
      render();
    });
  }

  const passwordForm = document.querySelector("[data-account-form='password']");
  if (passwordForm) {
    passwordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(passwordForm);
      await changePassword({
        currentPassword: formData.get("currentPassword"),
        newPassword: formData.get("newPassword"),
        confirmPassword: formData.get("confirmPassword")
      });
      render();
    });
  }

  document.querySelectorAll("[data-account-form] input").forEach((input) => {
    input.addEventListener("input", () => {
      if (state.accountSettings.error || state.accountSettings.success) {
        clearAccountSettingsMessage();
        const container = input.closest(".settings-main") || input.closest(".account-settings-card");
        container?.querySelectorAll(".alert").forEach((alert) => {
          alert.classList.remove("visible");
          alert.textContent = "";
        });
      }
    });
  });
}

function bindDropzone() {
  // Dropzone hanya ada di halaman upload, jadi fungsi ini aman return jika elemennya tidak ada.
  const dropzone = document.querySelector("[data-dropzone]");
  if (!dropzone) {
    return;
  }

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

function handleFile(file) {
  state.error = "";

  if (!file) {
    return;
  }

  // Validasi cepat di browser sebelum PDF dianalisis.
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

  if (state.selectedFileUrl) {
    URL.revokeObjectURL(state.selectedFileUrl);
  }
  state.selectedFile = file;
  state.selectedFileUrl = URL.createObjectURL(file);
  render();
}

function updateAnalyzeButton() {
  // Tombol analisis aktif hanya jika file valid dan target role sudah cukup jelas.
  const hasTarget = state.analysisMode === "auto" || state.targetRole.trim().length > 2;
  const canProceed = Boolean(state.selectedFile && hasTarget) && !state.isAnalyzing;
  const analyzeButton = document.querySelector("[data-action='analyze']");
  const reviewButton = document.querySelector("[data-upload-review-button]");

  if (analyzeButton) {
    analyzeButton.disabled = !canProceed;
  }

  if (reviewButton) {
    reviewButton.disabled = !canProceed;
  }
}

function canReviewUpload() {
  const hasTarget = state.analysisMode === "auto" || state.targetRole.trim().length > 2;
  return Boolean(state.selectedFile && hasTarget);
}
