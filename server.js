const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const cors = require("cors");
const express = require("express");
const multer = require("multer");
const { Pool } = require("pg");

const ROOT = __dirname;
const BACKEND_ROOT = path.join(ROOT, "backend");
loadEnvFile(path.join(BACKEND_ROOT, ".env"));

const app = express();
const port = Number(process.env.PORT || 5000);
const host = process.env.HOST || "127.0.0.1";
const isProduction = ["prod", "production"].includes(String(process.env.APP_ENV || "development").toLowerCase());
const upload = multer({
  dest: path.join(os.tmpdir(), "jobfit-uploads"),
  limits: { fileSize: Number(process.env.MAX_UPLOAD_SIZE || 5 * 1024 * 1024) }
});
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || process.env.POSTGRES_URL
});
const rateBuckets = new Map();

app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true }));
app.use(cors({ origin: corsOrigin(), credentials: false }));
app.use(securityHeaders);

app.get("/health", async (_request, response) => {
  try {
    const jobsCount = await scalar("SELECT COUNT(*)::int AS count FROM jobs");
    response.json({
      ok: true,
      service: "JobFit Express API",
      framework: "Express",
      database: "PostgreSQL",
      jobsSource: process.env.JOBS_SOURCE || "postgres",
      jobsCount
    });
  } catch (error) {
    response.status(500).json({ ok: false, detail: "Health check gagal.", error: error.message });
  }
});

app.post("/api/auth/register", async (request, response) => {
  try {
    const data = validateAuthPayload(request.body, true);
    enforceRateLimit("register", data.email, 5, 10 * 60);
    const user = await createOrUpdateUnverifiedUser(data.name, data.email, data.password);
    if (!user) {
      return response.status(409).json({ detail: "Email sudah terdaftar. Silakan masuk dengan akun tersebut." });
    }

    response.json(await issueRegisterOtp(user));
  } catch (error) {
    sendError(response, error, "Registrasi gagal diproses.");
  }
});

app.post("/api/auth/verify-otp", async (request, response) => {
  try {
    const verificationId = String(request.body?.verificationId || "").trim();
    const email = normalizeEmail(request.body?.email);
    const otp = String(request.body?.otp || "").trim();
    if (!verificationId || !isValidEmail(email) || !/^\d{6}$/.test(otp)) {
      return response.status(400).json({ detail: "Kode verifikasi tidak valid." });
    }

    enforceRateLimit("verify_otp", email, 8, 10 * 60);
    const result = await verifyEmailOtp(verificationId, email, otp);
    if (!result.ok) {
      const messages = {
        not_found: "Kode verifikasi tidak ditemukan.",
        consumed: "Kode verifikasi sudah digunakan.",
        expired: "Kode verifikasi sudah kedaluwarsa. Kirim ulang kode.",
        too_many_attempts: "Terlalu banyak percobaan kode. Kirim ulang kode.",
        invalid: "Kode verifikasi salah."
      };
      return response.status(400).json({ detail: messages[result.reason] || "Kode verifikasi tidak valid." });
    }

    response.json(await authResponse(result.user));
  } catch (error) {
    sendError(response, error, "Verifikasi OTP gagal diproses.");
  }
});

app.post("/api/auth/resend-otp", async (request, response) => {
  try {
    const email = normalizeEmail(request.body?.email);
    if (!isValidEmail(email)) {
      return response.status(400).json({ detail: "Masukkan alamat email yang valid." });
    }

    enforceRateLimit("resend_otp", email, 3, 10 * 60);
    const result = await createOtpForUnverifiedEmail(email);
    if (result.reason === "not_found") {
      return response.status(404).json({ detail: "Akun belum ditemukan. Silakan daftar ulang." });
    }
    if (result.reason === "verified") {
      return response.status(409).json({ detail: "Email sudah diverifikasi. Silakan masuk." });
    }

    response.json(await deliverOtpResponse(result.otpPayload));
  } catch (error) {
    sendError(response, error, "Kirim ulang OTP gagal diproses.");
  }
});

app.post("/api/auth/login", async (request, response) => {
  try {
    const data = validateAuthPayload(request.body, false);
    enforceRateLimit("login", data.email, 8, 10 * 60);
    const user = await authenticateUser(data.email, data.password);
    if (!user) {
      return response.status(401).json({ detail: "Email atau password tidak cocok." });
    }
    if (!user.emailVerified) {
      return response.status(403).json({ detail: "Email belum diverifikasi." });
    }

    response.json(await authResponse(user));
  } catch (error) {
    sendError(response, error, "Login gagal diproses.");
  }
});

app.get("/api/auth/me", async (request, response) => {
  try {
    response.json({ user: await requireUser(request) });
  } catch (error) {
    sendError(response, error, "Sesi login tidak valid. Silakan masuk ulang.");
  }
});

app.patch("/api/auth/me", async (request, response) => {
  try {
    const user = await requireUser(request);
    const name = String(request.body?.name || "").trim();
    if (name.length < 2) {
      return response.status(400).json({ detail: "Nama wajib diisi minimal 2 karakter." });
    }

    response.json({ user: await updateUser(user.id, name) });
  } catch (error) {
    sendError(response, error, "Profil gagal diperbarui.");
  }
});

app.post("/api/auth/change-password", async (request, response) => {
  try {
    const user = await requireUser(request);
    const currentPassword = String(request.body?.currentPassword || "");
    const newPassword = String(request.body?.newPassword || "");
    const confirmPassword = String(request.body?.confirmPassword || "");
    if (newPassword.length < 6) {
      return response.status(400).json({ detail: "Password baru minimal 6 karakter." });
    }
    if (newPassword !== confirmPassword) {
      return response.status(400).json({ detail: "Konfirmasi password baru tidak sama." });
    }

    if (!(await changeUserPassword(user.id, currentPassword, newPassword))) {
      return response.status(400).json({ detail: "Password saat ini tidak cocok." });
    }
    response.json({ ok: true });
  } catch (error) {
    sendError(response, error, "Password gagal diganti.");
  }
});

app.post("/api/auth/logout", async (request, response) => {
  await deleteSession(bearerToken(request.headers.authorization)).catch(() => null);
  response.json({ ok: true });
});

app.get("/api/analyses", async (request, response) => {
  try {
    const user = await requireUser(request);
    response.json({ analyses: await listUserAnalyses(user.id) });
  } catch (error) {
    sendError(response, error, "Riwayat analisis gagal dimuat.");
  }
});

app.get("/api/analyses/titles", async (request, response) => {
  try {
    const query = String(request.query.q || "").trim().toLowerCase();
    const titles = query ? await matchingJobTitles(query) : await defaultJobTitles();
    response.json({ titles });
  } catch (error) {
    sendError(response, error, "Saran pekerjaan gagal dimuat.");
  }
});

app.get("/api/analyses/:id", async (request, response) => {
  try {
    const user = await requireUser(request);
    const analysis = await getUserAnalysis(user.id, request.params.id);
    if (!analysis) {
      return response.status(404).json({ detail: "Hasil analisis tidak ditemukan." });
    }
    response.json(analysis);
  } catch (error) {
    sendError(response, error, "Detail analisis gagal dimuat.");
  }
});

app.post("/api/analyses", upload.single("cv"), async (request, response) => {
  const uploadedPath = request.file?.path;
  try {
    const mode = String(request.body?.analysisMode || "targeted").trim().toLowerCase();
    const token = bearerToken(request.headers.authorization);
    enforceRateLimit("analysis", token || request.ip || "anonymous", 8, 10 * 60);
    if (!["targeted", "auto"].includes(mode)) {
      return response.status(400).json({ detail: "Mode analisis tidak valid." });
    }

    const targetRole = String(request.body?.targetRole || "").trim();
    if (mode === "targeted" && targetRole.length < 3) {
      return response.status(400).json({ detail: "Target pekerjaan wajib diisi minimal 3 karakter." });
    }
    if (!request.file || !String(request.file.originalname || "").toLowerCase().endsWith(".pdf")) {
      return response.status(400).json({ detail: "File harus berformat PDF." });
    }

    const user = token ? await requireUser(request) : null;
    const result = await runPythonAnalysis(uploadedPath, targetRole, mode);
    const cvText = result._cvText || "";
    delete result._cvText;

    const payload = user ? await saveAnalysis(user.id, result, cvText) : result;
    response.json(payload);
  } catch (error) {
    sendError(response, error, "Analisis gagal diproses. Coba beberapa saat lagi.");
  } finally {
    if (uploadedPath) {
      fs.unlink(uploadedPath, () => {});
    }
  }
});

if (isProduction) {
  const distPath = path.join(ROOT, "dist");
  app.use(express.static(distPath));
  app.get("*", (_request, response) => {
    response.sendFile(path.join(distPath, "index.html"));
  });
}

start();

async function start() {
  validateProductionConfig();
  await ensureDatabaseSchema();
  await cleanupExpiredRecords();
  app.listen(port, host, () => {
    console.log(`JobFit Express API running at http://${host}:${port}`);
  });
}

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const index = trimmed.indexOf("=");
    const key = trimmed.slice(0, index).trim();
    const value = trimmed.slice(index + 1).trim().replace(/^['"]|['"]$/g, "");
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

function corsOrigin() {
  if (!isProduction) return "*";
  const origins = csvEnv("FRONTEND_ORIGINS");
  return origins.length ? origins : false;
}

function csvEnv(name) {
  return String(process.env[name] || "")
    .split(",")
    .map((item) => item.trim().replace(/\/$/, ""))
    .filter(Boolean);
}

function securityHeaders(request, response, next) {
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  response.setHeader("X-Frame-Options", "DENY");
  if (request.path.startsWith("/api/")) {
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("Pragma", "no-cache");
  }
  next();
}

function validateProductionConfig() {
  if (!isProduction) return;
  const errors = [];
  if (!(process.env.DATABASE_URL || process.env.POSTGRES_URL)) errors.push("DATABASE_URL atau POSTGRES_URL wajib diisi.");
  if (csvEnv("FRONTEND_ORIGINS").includes("*")) errors.push("FRONTEND_ORIGINS tidak boleh berisi wildcard '*'.");
  if (!(process.env.RESEND_API_KEY || process.env.SMTP_HOST)) errors.push("RESEND_API_KEY atau SMTP_HOST wajib diisi agar OTP production bisa dikirim.");
  if (!(process.env.EMAIL_FROM || process.env.SMTP_FROM || process.env.SMTP_USER)) errors.push("EMAIL_FROM, SMTP_FROM, atau SMTP_USER wajib diisi untuk pengirim OTP.");
  if (!process.env.RESEND_API_KEY && process.env.SMTP_USER && !process.env.SMTP_PASSWORD) errors.push("SMTP_PASSWORD wajib diisi jika SMTP_USER digunakan.");
  if (errors.length) throw new Error(`Konfigurasi production belum aman. ${errors.join(" ")}`);
}

async function ensureDatabaseSchema() {
  const schema = fs.readFileSync(path.join(BACKEND_ROOT, "database", "schema.sql"), "utf8");
  await pool.query(schema);
}

async function cleanupExpiredRecords() {
  await pool.query("DELETE FROM sessions WHERE expires_at <= NOW()");
  await pool.query("UPDATE email_otps SET consumed_at = NOW() WHERE expires_at <= NOW() AND consumed_at IS NULL");
}

async function scalar(sql, params = []) {
  const { rows } = await pool.query(sql, params);
  return rows[0]?.count || 0;
}

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateAuthPayload(payload, requireName) {
  const name = String(payload?.name || "").trim();
  const email = normalizeEmail(payload?.email);
  const password = String(payload?.password || "");
  if (requireName && name.length < 2) throw httpError(400, "Nama wajib diisi minimal 2 karakter.");
  if (!isValidEmail(email)) throw httpError(400, "Masukkan alamat email yang valid.");
  if (password.length < 6) throw httpError(400, "Password minimal 6 karakter.");
  return { name, email, password };
}

function hashPassword(password) {
  const iterations = 210000;
  const salt = crypto.randomBytes(16).toString("hex");
  const digest = crypto.pbkdf2Sync(String(password), salt, iterations, 32, "sha256").toString("hex");
  return `pbkdf2_sha256$${iterations}$${salt}$${digest}`;
}

function verifyPassword(password, storedHash) {
  const [algorithm, iterations, salt, digest] = String(storedHash || "").split("$");
  if (algorithm !== "pbkdf2_sha256" || !iterations || !salt || !digest) return false;
  const candidate = crypto.pbkdf2Sync(String(password), salt, Number(iterations), 32, "sha256").toString("hex");
  return crypto.timingSafeEqual(Buffer.from(candidate), Buffer.from(digest));
}

function hashSessionToken(token) {
  return `sha256$${crypto.createHash("sha256").update(String(token || "")).digest("hex")}`;
}

function publicUser(row) {
  if (!row) return null;
  return {
    id: String(row.id),
    name: row.name,
    email: row.email,
    emailVerified: Boolean(row.email_verified),
    createdAt: row.created_at ? new Date(row.created_at).toISOString() : null
  };
}

async function createOrUpdateUnverifiedUser(name, email, password) {
  const existing = await pool.query("SELECT id, email_verified FROM users WHERE email = $1", [normalizeEmail(email)]);
  if (existing.rows[0]?.email_verified) return null;

  const passwordHash = hashPassword(password);
  const result = existing.rows[0]
    ? await pool.query(
        "UPDATE users SET name = $1, password_hash = $2, updated_at = NOW() WHERE email = $3 RETURNING id, name, email, email_verified, created_at",
        [name, passwordHash, normalizeEmail(email)]
      )
    : await pool.query(
        "INSERT INTO users (name, email, password_hash, email_verified) VALUES ($1, $2, $3, FALSE) RETURNING id, name, email, email_verified, created_at",
        [name, normalizeEmail(email), passwordHash]
      );
  return publicUser(result.rows[0]);
}

async function authenticateUser(email, password) {
  const { rows } = await pool.query(
    "SELECT id, name, email, password_hash, email_verified, created_at FROM users WHERE email = $1",
    [normalizeEmail(email)]
  );
  const row = rows[0];
  if (!row || !verifyPassword(password, row.password_hash)) return null;
  return publicUser(row);
}

async function createSession(userId) {
  const token = crypto.randomBytes(32).toString("base64url");
  const expiresAt = new Date(Date.now() + Number(process.env.SESSION_DAYS || 30) * 24 * 60 * 60 * 1000);
  await pool.query("INSERT INTO sessions (token, user_id, expires_at) VALUES ($1, $2, $3)", [
    hashSessionToken(token),
    userId,
    expiresAt
  ]);
  return { token, expiresAt };
}

async function authResponse(user) {
  const session = await createSession(user.id);
  return { token: session.token, expiresAt: session.expiresAt.toISOString(), user };
}

async function createEmailOtp(userId, email, purpose = "register") {
  const otp = String(crypto.randomInt(0, 1000000)).padStart(6, "0");
  const expiresAt = new Date(Date.now() + Number(process.env.OTP_MINUTES || 10) * 60 * 1000);
  await pool.query("UPDATE email_otps SET consumed_at = NOW() WHERE user_id = $1 AND purpose = $2 AND consumed_at IS NULL", [
    userId,
    purpose
  ]);
  const { rows } = await pool.query(
    "INSERT INTO email_otps (user_id, email, otp_hash, purpose, expires_at) VALUES ($1, $2, $3, $4, $5) RETURNING id, email, expires_at",
    [userId, normalizeEmail(email), hashPassword(otp), purpose, expiresAt]
  );
  return {
    verificationId: String(rows[0].id),
    email: rows[0].email,
    expiresAt: new Date(rows[0].expires_at).toISOString(),
    otp
  };
}

async function issueRegisterOtp(user) {
  return deliverOtpResponse(await createEmailOtp(user.id, user.email));
}

async function deliverOtpResponse(otpPayload) {
  try {
    await sendOtpEmail(otpPayload.email, otpPayload.otp);
    return buildOtpResponse(otpPayload, true);
  } catch (error) {
    if (!isProduction) {
      console.warn(`OTP email delivery failed; using development fallback: ${error.message}`);
      return buildOtpResponse(otpPayload, false);
    }
    throw httpError(500, "Email OTP tidak terkirim. Coba beberapa saat lagi.");
  }
}

function buildOtpResponse(otpPayload, otpSent) {
  const response = {
    verificationId: otpPayload.verificationId,
    email: otpPayload.email,
    expiresAt: otpPayload.expiresAt,
    otpSent
  };
  if (!isProduction && !otpSent) response.devOtp = otpPayload.otp;
  return response;
}

async function sendOtpEmail(email, otp) {
  if (!process.env.SMTP_HOST || !(process.env.SMTP_FROM || process.env.SMTP_USER)) {
    throw new Error("SMTP belum dikonfigurasi.");
  }
  await runPythonCommand(path.join(BACKEND_ROOT, "scripts", "send_otp_cli.py"), ["--email", email, "--otp", otp]);
}

async function verifyEmailOtp(verificationId, email, otp, purpose = "register") {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const normalizedEmail = normalizeEmail(email);
    const { rows } = await client.query(
      "SELECT id, user_id, email, otp_hash, expires_at, attempts, consumed_at FROM email_otps WHERE id = $1 AND email = $2 AND purpose = $3",
      [verificationId, normalizedEmail, purpose]
    );
    let row = rows[0];
    if (!row || row.consumed_at) {
      const latest = await client.query(
        `SELECT id, user_id, email, otp_hash, expires_at, attempts, consumed_at
         FROM email_otps
         WHERE email = $1
           AND purpose = $2
           AND consumed_at IS NULL
           AND expires_at > NOW()
           AND attempts < $3
         ORDER BY created_at DESC
         LIMIT 1`,
        [normalizedEmail, purpose, Number(process.env.MAX_OTP_ATTEMPTS || 5)]
      );
      row = latest.rows[0] || row;
    }
    if (!row) return { ok: false, reason: "not_found" };
    if (row.consumed_at) return { ok: false, reason: "consumed" };
    if (new Date(row.expires_at) <= new Date()) return { ok: false, reason: "expired" };
    if (Number(row.attempts || 0) >= Number(process.env.MAX_OTP_ATTEMPTS || 5)) return { ok: false, reason: "too_many_attempts" };
    if (!verifyPassword(otp, row.otp_hash)) {
      await client.query("UPDATE email_otps SET attempts = attempts + 1 WHERE id = $1", [verificationId]);
      await client.query("COMMIT");
      return { ok: false, reason: "invalid" };
    }
    await client.query("UPDATE email_otps SET consumed_at = NOW() WHERE id = $1", [verificationId]);
    const userResult = await client.query(
      "UPDATE users SET email_verified = TRUE, updated_at = NOW() WHERE id = $1 RETURNING id, name, email, email_verified, created_at",
      [row.user_id]
    );
    await client.query("COMMIT");
    return { ok: true, user: publicUser(userResult.rows[0]) };
  } catch (error) {
    await client.query("ROLLBACK").catch(() => null);
    throw error;
  } finally {
    client.release();
  }
}

async function createOtpForUnverifiedEmail(email) {
  const { rows } = await pool.query("SELECT id, name, email, email_verified, created_at FROM users WHERE email = $1", [
    normalizeEmail(email)
  ]);
  if (!rows[0]) return { reason: "not_found" };
  if (rows[0].email_verified) return { reason: "verified" };
  return { otpPayload: await createEmailOtp(rows[0].id, rows[0].email) };
}

function bearerToken(authorization) {
  const prefix = "Bearer ";
  return typeof authorization === "string" && authorization.startsWith(prefix) ? authorization.slice(prefix.length).trim() : "";
}

async function getUserByToken(token) {
  if (!token) return null;
  await pool.query("DELETE FROM sessions WHERE expires_at <= NOW()");
  const { rows } = await pool.query(
    "SELECT users.id, users.name, users.email, users.email_verified, users.created_at FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token = $1 AND sessions.expires_at > NOW()",
    [hashSessionToken(token)]
  );
  return publicUser(rows[0]);
}

async function requireUser(request) {
  const user = await getUserByToken(bearerToken(request.headers.authorization));
  if (!user) throw httpError(401, "Sesi login tidak valid. Silakan masuk ulang.");
  return user;
}

async function deleteSession(token) {
  if (token) await pool.query("DELETE FROM sessions WHERE token = $1", [hashSessionToken(token)]);
}

async function updateUser(userId, name) {
  const { rows } = await pool.query(
    "UPDATE users SET name = $1, updated_at = NOW() WHERE id = $2 RETURNING id, name, email, email_verified, created_at",
    [name, userId]
  );
  return publicUser(rows[0]);
}

async function changeUserPassword(userId, currentPassword, newPassword) {
  const { rows } = await pool.query("SELECT password_hash FROM users WHERE id = $1", [userId]);
  if (!rows[0] || !verifyPassword(currentPassword, rows[0].password_hash)) return false;
  await pool.query("UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2", [hashPassword(newPassword), userId]);
  return true;
}

async function listUserAnalyses(userId) {
  const { rows } = await pool.query(
    "SELECT id, target_role, analysis_mode, score, verdict, result_json, created_at FROM analyses WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50",
    [userId]
  );
  return rows.map(analysisListItem);
}

async function getUserAnalysis(userId, analysisId) {
  const { rows } = await pool.query("SELECT result_json, created_at FROM analyses WHERE user_id = $1 AND id = $2", [userId, analysisId]);
  if (!rows[0]) return null;
  const result = parseResultJson(rows[0].result_json);
  if (!result.date) result.date = formatDate(rows[0].created_at);
  return result;
}

async function saveAnalysis(userId, result, cvText) {
  const analysisId = String(result.id || `analysis-${crypto.randomUUID()}`);
  const payload = { ...result, id: analysisId };
  await pool.query(
    `INSERT INTO analyses (id, user_id, target_role, analysis_mode, score, verdict, cv_text, result_json)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
     ON CONFLICT (id) DO UPDATE SET
       target_role = EXCLUDED.target_role,
       analysis_mode = EXCLUDED.analysis_mode,
       score = EXCLUDED.score,
       verdict = EXCLUDED.verdict,
       cv_text = EXCLUDED.cv_text,
       result_json = EXCLUDED.result_json`,
    [
      analysisId,
      userId,
      payload.targetRole || "Analisis CV",
      payload.analysisMode || "targeted",
      Number(payload.score || 0),
      payload.verdict || "Analisis Selesai",
      cvText,
      payload
    ]
  );
  return payload;
}

function analysisListItem(row) {
  const result = parseResultJson(row.result_json);
  result.id = row.id;
  result.date = result.date || formatDate(row.created_at);
  result.targetRole = result.targetRole || row.target_role;
  result.analysisMode = result.analysisMode || row.analysis_mode;
  result.score = Number(result.score || row.score || 0);
  result.verdict = result.verdict || row.verdict;
  result.status = "Selesai";
  return result;
}

function parseResultJson(value) {
  if (!value) return {};
  return typeof value === "string" ? JSON.parse(value) : value;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("id-ID", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}

async function defaultJobTitles() {
  const { rows } = await pool.query("SELECT DISTINCT title FROM jobs WHERE title IS NOT NULL AND title <> '' ORDER BY title LIMIT 20");
  return rows.map((row) => row.title);
}

async function matchingJobTitles(query) {
  const { rows } = await pool.query(
    "SELECT DISTINCT title FROM jobs WHERE title ILIKE $1 AND title IS NOT NULL AND title <> '' ORDER BY title LIMIT 20",
    [`%${query}%`]
  );
  return rows.map((row) => row.title);
}

function runPythonAnalysis(pdfPath, targetRole, analysisMode) {
  return runPythonCommand(path.join(BACKEND_ROOT, "scripts", "analyze_cli.py"), [
    "--pdf",
    pdfPath,
    "--target-role",
    targetRole,
    "--analysis-mode",
    analysisMode
  ]).then((stdout) => JSON.parse(stdout));
}

function runPythonCommand(script, args) {
  return new Promise((resolve, reject) => {
    const python = pythonExecutable();
    const timeoutMs = Number(process.env.PYTHON_ANALYSIS_TIMEOUT_MS || 60000);
    let settled = false;
    const child = spawn(python, [script, ...args], {
      cwd: BACKEND_ROOT,
      env: {
        ...process.env,
        JOBFIT_ENABLE_SEMANTIC_MODEL: process.env.JOBFIT_ENABLE_SEMANTIC_MODEL || (isProduction ? "false" : "true"),
        JOBFIT_ENABLE_GEMINI: process.env.JOBFIT_ENABLE_GEMINI || (isProduction ? "false" : "true"),
        GEMINI_TIMEOUT_SECONDS: process.env.GEMINI_TIMEOUT_SECONDS || "12",
        PYTHONPATH: [path.join(ROOT, ".codex-python-packages"), BACKEND_ROOT].filter(fs.existsSync).join(path.delimiter)
      }
    });
    const timeout = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGTERM");
      reject(httpError(504, "Analisis membutuhkan waktu terlalu lama. Coba CV PDF teks yang lebih ringkas atau ulangi beberapa saat lagi."));
    }, timeoutMs);
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      reject(error);
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (code !== 0) {
        return reject(new Error(stderr || `Python analysis exited with code ${code}`));
      }
      resolve(stdout.trim());
    });
  });
}

function pythonExecutable() {
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH;
  const bundled = path.join(os.homedir(), ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "python", "python.exe");
  return fs.existsSync(bundled) ? bundled : "python";
}

function enforceRateLimit(bucket, key, limit, windowSeconds) {
  const id = `${bucket}:${key}`;
  const now = Date.now();
  const windowMs = windowSeconds * 1000;
  const entry = rateBuckets.get(id) || { count: 0, resetAt: now + windowMs };
  if (entry.resetAt <= now) {
    entry.count = 0;
    entry.resetAt = now + windowMs;
  }
  entry.count += 1;
  rateBuckets.set(id, entry);
  if (entry.count > limit) {
    throw httpError(429, "Terlalu banyak request. Coba beberapa saat lagi.");
  }
}

function httpError(status, detail) {
  const error = new Error(detail);
  error.status = status;
  error.detail = detail;
  return error;
}

function sendError(response, error, fallback) {
  const status = error.status || 500;
  const detail = error.detail || (status < 500 ? error.message : fallback);
  if (status >= 500) console.error(error);
  response.status(status).json({ detail });
}
