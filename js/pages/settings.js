import { shell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

export function renderSettings() {
  const user = state.auth.user || { name: "User JobFit", email: "-" };

  return shell(`
    <section class="page-title">
      <div class="container">
        <h1>Pengaturan Akun</h1>
        <p>Kelola profil dan keamanan akun JobFit yang tersimpan di database.</p>
      </div>
    </section>

    <section class="container settings-layout">
      <div class="settings-main">
        ${renderAccountSettingsMessage()}

        <article class="card dashboard-card account-settings-card">
          <h3>Profil Akun</h3>
          <p>Perbarui nama yang tampil di navbar dan dashboard user.</p>
          <form class="account-settings-form" data-account-form="profile" novalidate>
            <div class="form-field">
              <label for="accountName">Nama lengkap</label>
              <input
                class="text-input"
                id="accountName"
                name="name"
                type="text"
                value="${escapeHtml(user.name)}"
                autocomplete="name"
                required
              />
            </div>
            <div class="readonly-field">
              <span>Email akun</span>
              <strong>${escapeHtml(user.email)}</strong>
              <p>Email akan dikelola lewat verifikasi OTP pada tahap berikutnya.</p>
            </div>
            <button class="btn btn-primary" type="submit">Simpan Profil</button>
          </form>
        </article>

        <article class="card dashboard-card account-settings-card">
          <h3>Keamanan</h3>
          <p>Ganti password akun Anda. Password baru akan dipakai saat login berikutnya.</p>
          <form class="account-settings-form" data-account-form="password" novalidate>
            <div class="form-field">
              <label for="currentPassword">Password saat ini</label>
              <div style="position: relative; display: flex; align-items: center;">
                <input
                  class="text-input"
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  autocomplete="current-password"
                  required
                  style="width: 100%; padding-right: 40px;"
                />
                <button type="button" data-action="toggle-password" data-target="currentPassword" style="position: absolute; right: 12px; background: none; border: none; cursor: pointer; color: var(--muted); font-size: 16px; padding: 4px; display: flex; align-items: center; justify-content: center;" aria-label="Tampilkan password">👁️</button>
              </div>
            </div>
            <div class="account-password-grid">
              <div class="form-field">
                <label for="newPassword">Password baru</label>
                <div style="position: relative; display: flex; align-items: center;">
                  <input
                    class="text-input"
                    id="newPassword"
                    name="newPassword"
                    type="password"
                    autocomplete="new-password"
                    minlength="6"
                    required
                    style="width: 100%; padding-right: 40px;"
                  />
                  <button type="button" data-action="toggle-password" data-target="newPassword" style="position: absolute; right: 12px; background: none; border: none; cursor: pointer; color: var(--muted); font-size: 16px; padding: 4px; display: flex; align-items: center; justify-content: center;" aria-label="Tampilkan password">👁️</button>
                </div>
              </div>
              <div class="form-field">
                <label for="confirmPassword">Konfirmasi password</label>
                <div style="position: relative; display: flex; align-items: center;">
                  <input
                    class="text-input"
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autocomplete="new-password"
                    minlength="6"
                    required
                    style="width: 100%; padding-right: 40px;"
                  />
                  <button type="button" data-action="toggle-password" data-target="confirmPassword" style="position: absolute; right: 12px; background: none; border: none; cursor: pointer; color: var(--muted); font-size: 16px; padding: 4px; display: flex; align-items: center; justify-content: center;" aria-label="Tampilkan password">👁️</button>
                </div>
              </div>
            </div>
            <button class="btn btn-secondary" type="submit">Ganti Password</button>
          </form>
        </article>
      </div>

      <aside class="card account-panel">
        <h3>Ringkasan Akun</h3>
        <div class="account-profile-row">
          <span>Nama</span>
          <strong>${escapeHtml(user.name)}</strong>
        </div>
        <div class="account-profile-row">
          <span>Email</span>
          <strong>${escapeHtml(user.email)}</strong>
        </div>
        <div class="account-shortcuts">
          <a href="#/account" class="btn btn-secondary">Dashboard User</a>
          <a href="#/upload" class="btn btn-primary">Analisis CV Baru</a>
          <a href="#/history" class="btn btn-secondary">Riwayat Analisis</a>
        </div>
      </aside>
    </section>
  `);
}

function renderAccountSettingsMessage() {
  const { error, success } = state.accountSettings;

  return `
    <div class="alert alert-success ${success ? "visible" : ""}">
      ${escapeHtml(success)}
    </div>
    <div class="alert alert-error ${error ? "visible" : ""}">
      ${escapeHtml(error)}
    </div>
  `;
}
