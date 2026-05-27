// File ini berisi helper kecil yang dipakai lintas halaman.

export function getInitialTheme() {
  // Prioritas theme: pilihan user di localStorage, lalu preferensi OS.
  const savedTheme = window.localStorage.getItem("jobfit-theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    return savedTheme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
  // CSS membaca data-theme di elemen html untuk mengganti warna light/dark.
  document.documentElement.dataset.theme = theme;
}

export function syncAnchorScroll() {
  // Link seperti #/#features perlu scroll manual setelah halaman landing dirender.
  const hash = window.location.hash;
  if (hash.includes("#features") || hash.includes("#workflow") || hash.includes("#settings")) {
    const id = hash.split("#").at(-1);
    window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  } else {
    window.scrollTo({ top: 0 });
  }
}

export function initAnimations() {
  // Tambahkan class reveal ke elemen penting, lalu IntersectionObserver memicu animasinya.
  document
    .querySelectorAll(".card, .eyebrow, .hero h1, .hero-copy, .hero-actions, .hero-metrics, .page-title")
    .forEach((element) => {
      element.classList.add("reveal");
    });

  const revealElements = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealElements.forEach((element) => observer.observe(element));
  } else {
    revealElements.forEach((element) => element.classList.add("revealed"));
  }

  document.querySelectorAll("[data-count-to]").forEach((element) => animateCount(element));
}

function animateCount(element) {
  // Animasi angka dipakai untuk score dan statistik ringkas.
  const target = Number(element.dataset.countTo || 0);
  const hasPercent = element.textContent.includes("%");
  const duration = 850;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(target * eased);
    element.textContent = `${value}${hasPercent ? "%" : ""}`;

    if (progress < 1) {
      window.requestAnimationFrame(tick);
    }
  }

  window.requestAnimationFrame(tick);
}

export function formatBytes(bytes) {
  // Ubah ukuran file byte menjadi KB/MB agar mudah dibaca user.
  if (!bytes) {
    return "0 KB";
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  return `${(kb / 1024).toFixed(2)} MB`;
}

export function formatNumber(value) {
  // Format angka mengikuti locale Indonesia, contoh: 10.785.
  return Number(value || 0).toLocaleString("id-ID");
}

export function getClockTime() {
  // Format waktu singkat untuk label aktivitas UI.
  return new Date().toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function readStorage(key, fallbackValue) {
  // Wrapper aman untuk localStorage agar data rusak tidak membuat render gagal.
  try {
    const rawValue = window.localStorage.getItem(key);
    return rawValue ? JSON.parse(rawValue) : fallbackValue;
  } catch (error) {
    window.localStorage.removeItem(key);
    return fallbackValue;
  }
}

export function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    return false;
  }
}

export function escapeHtml(value) {
  // Penting untuk mencegah teks dari input/API berubah menjadi HTML aktif.
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
