import { authShell } from "../layout.js";
import { state } from "../state.js";
import { escapeHtml } from "../utils.js";

export function renderVerifyOtp() {
  const pending = state.verification.pending;
  const email = pending?.email || "email Anda";
  const expiresAt = pending?.expiresAt ? new Date(pending.expiresAt) : null;
  const expiresLabel = expiresAt && !Number.isNaN(expiresAt.getTime())
    ? expiresAt.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })
    : "10 menit";

  return authShell(`
    <section class="auth-section">
      <div class="container auth-layout">
        <div class="auth-copy">
          <p class="eyebrow">Verifikasi Email</p>
          <h1>Masukkan kode OTP untuk mengaktifkan akun</h1>
          <p>
            Kami mengirim kode verifikasi 6 digit ke ${escapeHtml(email)}.
            Kode berlaku sampai ${escapeHtml(expiresLabel)}.
          </p>
          <div class="auth-highlights">
            <span class="metric-pill"><span class="metric-dot"></span>OTP 6 digit</span>
            <span class="metric-pill"><span class="metric-dot"></span>Berlaku 10 menit</span>
            <span class="metric-pill"><span class="metric-dot"></span>Email terverifikasi</span>
          </div>
        </div>

        <article class="card auth-card">
          <div class="auth-card-header">
            <h2>Verifikasi OTP</h2>
            <p>Masukkan kode yang dikirim ke email Anda.</p>
          </div>

          <form class="auth-form" data-auth-form="verify-otp" novalidate>
            <div class="form-field">
              <label for="otpCode">Kode OTP</label>
              <input class="text-input otp-input" id="otpCode" name="otp" type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code" placeholder="000000" />
            </div>

            <div class="alert alert-error ${state.verification.error ? "visible" : ""}">
              ${escapeHtml(state.verification.error)}
            </div>
            <div class="alert alert-success ${state.verification.success ? "visible" : ""}">
              ${escapeHtml(state.verification.success)}
            </div>

            <button class="btn btn-primary auth-submit" type="submit">Verifikasi & Masuk</button>
          </form>

          <p class="auth-switch">
            Belum menerima kode?
            <button class="link-button" type="button" data-action="resend-otp">Kirim ulang</button>
          </p>
        </article>
      </div>
    </section>
  `);
}
