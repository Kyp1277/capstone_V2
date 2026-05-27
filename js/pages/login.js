import { authShell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

export function renderLogin() {
  return authShell(`
    <section class="auth-section">
      <div class="container auth-layout">
        <div class="auth-copy">
          <p class="eyebrow">Masuk Akun</p>
          <h1>Selamat datang kembali di JobFit</h1>
          <p>
            Masuk untuk membuka dashboard user, menjalankan analisis CV, melihat hasil terakhir,
            dan mengakses riwayat analisis yang tersimpan di akun Anda.
          </p>
          <div class="auth-highlights">
            <span class="metric-pill"><span class="metric-dot"></span>Dashboard user</span>
            <span class="metric-pill"><span class="metric-dot"></span>Riwayat analisis</span>
            <span class="metric-pill"><span class="metric-dot"></span>Database akun</span>
          </div>
        </div>

        <article class="card auth-card">
          <div class="auth-card-header">
            <h2>Masuk</h2>
            <p>Gunakan akun yang sudah tersimpan di database JobFit.</p>
          </div>

          <form class="auth-form" data-auth-form="login" novalidate>
            <div class="form-field">
              <label for="loginEmail">Email</label>
              <input class="text-input" id="loginEmail" name="email" type="email" autocomplete="email" placeholder="nama@email.com" />
            </div>

            <div class="form-field">
              <label for="loginPassword">Password</label>
              <input class="text-input" id="loginPassword" name="password" type="password" autocomplete="current-password" placeholder="Minimal 6 karakter" />
            </div>

            <div class="alert alert-error ${state.auth.error ? "visible" : ""}">
              ${escapeHtml(state.auth.error)}
            </div>

            <button class="btn btn-primary auth-submit" type="submit">Masuk ke Dashboard</button>
          </form>

          <p class="auth-switch">
            Belum punya akun?
            <a href="#/register">Daftar sekarang</a>
          </p>
        </article>
      </div>
    </section>
  `);
}
