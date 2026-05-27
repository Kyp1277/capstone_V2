import { shell } from "../layout.js";

// Fallback ketika hash route tidak ada di daftar routes.
export function renderNotFound() {
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
