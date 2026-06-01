# JobFit UI Prototype

JobFit adalah prototype aplikasi web untuk analisis CV berbasis AI. Frontend tetap statis dengan hash routing, sedangkan backend FastAPI terhubung ke PostgreSQL untuk dataset lowongan, akun, session, dan riwayat analisis.

## Halaman

- Landing Page: hero, fitur utama, cara kerja, dan CTA.
- Upload CV: drag and drop PDF, input target pekerjaan, state selected/loading/error.
- Dashboard Hasil: match score, ringkasan AI, detected skills, missing skills, rekomendasi CV, rekomendasi pekerjaan.
- Riwayat Analisis: daftar analisis yang tersimpan di database akun.
- 404 Page: fallback route untuk halaman tidak ditemukan.

## Struktur

- `index.html`: entry point aplikasi.
- `styles.css`: style guide, layout responsive, komponen UI.
- `js/main.js`: bootstrap aplikasi, render awal, dan hashchange listener.
- `js/state.js`: state global frontend, konfigurasi URL API, session, filter riwayat, dan cache analisis.
- `js/router.js`: hash router dan pemilihan renderer halaman.
- `js/layout.js`: shell halaman, navbar, footer, dan tombol theme.
- `js/pages/`: renderer per halaman (`landing`, `upload`, `dashboard`, `history`, dan `not-found`).
- `js/events.js`: event listener untuk theme, menu mobile, upload/dropzone, analisis CV, dan filter history.
- `js/api.js`: integrasi analisis CV dan riwayat melalui endpoint `/api/analyses`.
- `js/utils.js`: helper umum seperti format angka/file, escape HTML, theme, scroll anchor, dan animasi.
- `static-server.js`: server statis kecil untuk preview lokal.

## Menjalankan Preview

Jalankan backend API terlebih dahulu:

```powershell
.\backend\run-api.ps1
```

Backend memakai FastAPI dan berjalan di:

```text
http://127.0.0.1:5000
```

Dokumentasi endpoint otomatis:

```text
http://127.0.0.1:5000/docs
```

Buka terminal kedua untuk frontend:

```powershell
node static-server.js
```

Lalu buka:

```text
http://127.0.0.1:4173/
```

Frontend akan mengirim upload PDF ke:

```text
http://127.0.0.1:5000/api/analyses
```

Jika backend dijalankan di alamat lain, set melalui browser console:

```js
localStorage.setItem("jobfitApiBaseUrl", "http://127.0.0.1:5000")
```

## Hosting Aman

Untuk hosting, gunakan `backend\.env.production.example` sebagai template. Set minimal:

```text
APP_ENV=production
DATABASE_URL=postgresql://user:password@host:5432/jobfit
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=password_smtp
SMTP_FROM=noreply@example.com
SMTP_TLS=true
```

Jika frontend dan API berada pada domain yang sama lewat reverse proxy, `FRONTEND_ORIGINS` boleh kosong. Jika beda domain, isi whitelist origin frontend:

```text
FRONTEND_ORIGINS=https://jobfit.example.com,https://www.jobfit.example.com
```

Saat `APP_ENV=production`, backend menolak konfigurasi berbahaya seperti CORS wildcard, database kosong, atau SMTP OTP belum siap. OTP development (`devOtp`) tidak pernah dikirim pada production. Teks CV hasil ekstraksi tetap disimpan penuh di database sesuai kebutuhan riwayat/internal, tetapi tidak dikirim balik lewat response API.

Jika menjalankan backend dengan Python manual:

```powershell
cd backend
pip install -r requirements.txt
python api.py
```

## Validasi Backend

Jalankan dari root project:

```powershell
python -m py_compile backend\api.py backend\routes\__init__.py backend\routes\auth.py backend\routes\analyses.py backend\routes\health.py backend\modules\analysis_service.py backend\modules\auth_service.py backend\modules\config.py backend\modules\cv_parser.py backend\modules\data_loader.py backend\modules\database.py backend\modules\env_loader.py backend\modules\jobs_service.py backend\modules\nlp.py backend\modules\rate_limit.py backend\modules\test_work_experience.py backend\modules\test_api_contract.py backend\modules\test_database_contract.py backend\modules\test_recommendation_evaluation.py
```

Test ekstraksi pengalaman kerja:

```powershell
python backend\modules\test_work_experience.py
```

Test kontrak response API tanpa PDF eksternal:

```powershell
python backend\modules\test_api_contract.py
```

Test kontrak akun, session, dan riwayat PostgreSQL:

```powershell
python backend\modules\test_database_contract.py
```

Test OCR parser dan database skill:

```powershell
python backend\modules\test_cv_parser_ocr.py
python backend\modules\test_nlp_soft_skills.py
python backend\modules\test_security_hardening.py
python backend\modules\test_frontend_hosting_contract.py
```

Test evaluasi rekomendasi dengan CV synthetic/anonymized:

```powershell
python backend\modules\test_recommendation_evaluation.py
```

## Dataset PostgreSQL

Backend membaca dataset lowongan dari PostgreSQL dan memakai database yang sama untuk akun, session, serta riwayat analisis. Jika `DATABASE_URL` tidak diisi, dataset lowongan bisa fallback ke CSV, tetapi fitur akun dan riwayat database membutuhkan PostgreSQL.

### Setup otomatis

Jika PostgreSQL sudah terinstall lokal, jalankan:

```powershell
.\backend\scripts\setup-postgres.ps1
```

Script ini akan meminta password user `postgres`, membuat database `jobfit` jika belum ada, menulis `backend\.env`, import dataset jobs, dan mengecek jumlah data.

### Setup manual

1. Buat database PostgreSQL, lalu set koneksi:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`, lalu ganti `password_kamu` dengan password PostgreSQL lokal:

```text
DATABASE_URL=postgresql://postgres:password_kamu@localhost:5432/jobfit
JOBS_SOURCE=postgres
JOBS_TABLE=jobs
HOST=127.0.0.1
PORT=5000
APP_ENV=development
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TLS=true
```

2. Import dataset CSV yang sudah ada ke PostgreSQL:

```powershell
cd backend
python scripts/import_jobs_to_postgres.py
```

Script import akan membuat tabel `jobs` jika belum ada, menambahkan index pencarian, lalu melakukan upsert dataset berdasarkan `fingerprint`. Kolom dataset yang dimuat:

```text
job_no, title, company, location, keyword, job_url, description, scraped_at, fingerprint
```

3. Cek koneksi dan jumlah data:

```powershell
python scripts/check_postgres_jobs.py
```

Output yang diharapkan:

```text
Koneksi PostgreSQL berhasil.
Total jobs: 10785
```

4. Jalankan API:

```powershell
python api.py
```

Saat API start, schema `jobs`, `users`, `sessions`, `email_otps`, dan `analyses` dibuat/di-update otomatis dari `backend/database/schema.sql`. Endpoint `/health` akan menampilkan `jobsSource` dan jumlah data yang dibaca. Untuk memaksa dataset kembali ke CSV:

```powershell
$env:JOBS_SOURCE="csv"
```

Endpoint `/health` tetap tersedia untuk pengecekan teknis saat pengembangan.

### Mode demo stabil

Untuk presentasi tanpa upload ulang, buat akun demo dan satu riwayat analisis contoh:

```powershell
python backend\scripts\seed_demo_account.py
```

Login demo:

```text
Email: demo@jobfit.local
Password: demo1234
```

Akun demo tetap memakai tabel `users` dan `analyses`, sehingga dashboard dan riwayat membaca data dari database yang sama.

## Kontrak API

Endpoint akun:

```text
POST /api/auth/register
POST /api/auth/verify-otp
POST /api/auth/resend-otp
POST /api/auth/login
GET /api/auth/me
PATCH /api/auth/me
POST /api/auth/change-password
POST /api/auth/logout
```

`register` membuat akun belum terverifikasi dan mengirim OTP email. Response register berisi `verificationId`, `email`, `expiresAt`, dan `devOtp` hanya saat `APP_ENV=development`. Setelah `verify-otp` berhasil, backend mengembalikan `token` serta `user`. Frontend mengirim token melalui header:

```text
Authorization: Bearer <token>
```

Halaman upload mengirim request ke backend:

```text
POST /api/analyses
Content-Type: multipart/form-data

fields:
- cv: File PDF
- targetRole: string
- analysisMode: targeted | auto
```

Jika token valid dikirim, hasil analisis otomatis disimpan ke tabel `analyses` bersama teks CV hasil ekstraksi. File PDF mentah tidak disimpan.
Endpoint auth, OTP, dan upload memakai rate limit ringan in-memory untuk mengurangi spam saat demo.

Response yang diharapkan untuk implementasi full-stack:

```json
{
  "id": "analysis-001",
  "targetRole": "Frontend Developer",
  "score": 82,
  "detectedSkills": ["HTML", "CSS", "JavaScript", "React"],
  "workExperiences": [],
  "totalExperienceYears": 0,
  "experienceLevel": "entry_level",
  "experienceMatch": 0,
  "missingSkills": ["TypeScript", "Unit Testing"],
  "improvements": ["Tambahkan project React yang menggunakan API."],
  "jobs": [
    {
      "title": "Frontend Developer",
      "match": 88
    }
  ]
}
```

Response job recommendation juga menyertakan `matchedSkills`, `missingSkills`, `notFitReason`, `improvements`, dan `scoreBreakdown` untuk kebutuhan dashboard hasil analisis.

Endpoint riwayat:

```text
GET /api/analyses
GET /api/analyses/{id}
```

Keduanya membutuhkan token login dan hanya mengembalikan riwayat milik akun tersebut.
