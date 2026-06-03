import { authShell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

export function renderRegister() {
  return authShell(`
    <section class="auth-section">
      <div class="container auth-layout">
        <div class="auth-copy">
          <p class="eyebrow">Daftar Akun</p>
          <h1>Buat akun JobFit untuk mulai analisis CV</h1>
          <p>
            Buat akun untuk menyimpan riwayat analisis dan membuka kembali hasil CV Anda
            dari akun Anda.
          </p>
          <div class="auth-highlights">
            <span class="metric-pill"><span class="metric-dot"></span>Nama user</span>
            <span class="metric-pill"><span class="metric-dot"></span>Email unik</span>
            <span class="metric-pill"><span class="metric-dot"></span>OTP email</span>
          </div>
        </div>

        <article class="card auth-card">
          <div class="auth-card-header">
            <h2>Daftar</h2>
            <p>Isi data dasar untuk membuat akun JobFit di database.</p>
          </div>

          <form class="auth-form" data-auth-form="register" novalidate>
            <div class="form-field">
              <label for="registerName">Nama lengkap</label>
              <input class="text-input" id="registerName" name="name" type="text" autocomplete="name" placeholder="Nama Anda" />
            </div>

            <div class="form-field">
              <label for="registerEmail">Email</label>
              <input class="text-input" id="registerEmail" name="email" type="email" autocomplete="email" placeholder="nama@email.com" />
            </div>

            <div class="form-field">
              <label for="registerPassword">Password</label>
              <div style="position: relative; display: flex; align-items: center;">
                <input class="text-input" id="registerPassword" name="password" type="password" autocomplete="new-password" placeholder="Minimal 6 karakter" style="width: 100%; padding-right: 40px;" />
                <button type="button" data-action="toggle-password" data-target="registerPassword" style="position: absolute; right: 12px; background: none; border: none; cursor: pointer; color: var(--muted); font-size: 16px; padding: 4px; display: flex; align-items: center; justify-content: center;" aria-label="Tampilkan password">👁️</button>
              </div>
              <span class="helper-text">Setelah daftar, Anda akan menerima kode OTP untuk verifikasi email.</span>
            </div>

            <div class="alert alert-error ${state.auth.error ? "visible" : ""}">
              ${escapeHtml(state.auth.error)}
            </div>

            <button class="btn btn-primary auth-submit" type="submit">Buat Akun</button>
          </form>

          <p class="auth-switch">
            Sudah punya akun?
            <a href="#/login">Masuk</a>
          </p>
        </article>
      </div>
    </section>
  `);
}
