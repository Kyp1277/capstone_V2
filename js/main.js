import "./tailwind.css";
import { render } from "./router.js";
import { state } from "./state.js";
import { restoreSession } from "./auth.js";

// Entry point aplikasi: render awal dan pantau perubahan route.
window.addEventListener("hashchange", () => {
  // Saat pindah halaman, menu mobile dan dropdown akun ditutup agar UI selalu kembali rapi.
  state.mobileMenuOpen = false;
  state.accountMenuOpen = false;
  render();
});

// Render pertama cepat memakai cache, lalu sinkronkan session dan riwayat dari database.
render();
restoreSession().finally(render);
