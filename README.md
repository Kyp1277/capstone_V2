---
title: JobFit Backend
emoji: 💼
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# JobFit - AI CV Match Analyzer

JobFit adalah aplikasi full-stack untuk menganalisis CV PDF, menghitung match score, menemukan missing skills, dan memberi rekomendasi pekerjaan berbasis AI lokal. Stack utama proyek ini disesuaikan dengan checklist Dicoding: **Vite**, **Axios**, **Tailwind CSS**, **Express**, **RESTful API**, **PostgreSQL**, dan engine analisis Python.

## Checklist Dicoding

- Module bundler: Vite melalui `npm run dev`, `npm run build`, dan `npm run preview`.
- Networking calls: Axios client terpusat di `js/http.js`.
- RESTful API: Express di `server.js` dengan endpoint `/api/auth/*`, `/api/analyses`, dan `/api/analyses/:id`.
- Database: PostgreSQL untuk `jobs`, `users`, `sessions`, `email_otps`, dan `analyses`.
- AI/ML: Python analysis engine memakai parser CV, rule-based scoring, taxonomy role, BM25/IDF lokal, dan token-cosine fallback. Rekomendasi pekerjaan tidak memakai TensorFlow Hub, ChatGPT/Gemini API, OpenAI API, AutoML, atau pretrained semantic model.
- Responsive UI: layout responsif di `styles.css` plus Tailwind CSS build pipeline.
- Deployment config: `render.yaml` untuk full-stack deploy dan Express bisa serve hasil `dist` pada production.

## Struktur Utama

- `index.html`: entry HTML Vite.
- `js/main.js`: entry module frontend.
- `js/http.js`: Axios instance dan normalisasi error API.
- `js/pages/`: renderer halaman landing, upload, dashboard, riwayat, akun, dan auth.
- `styles.css` dan `js/tailwind.css`: styling custom dan Tailwind pipeline.
- `server.js`: Express REST API utama.
- `backend/scripts/analyze_cli.py`: bridge Express ke engine AI Python.
- `backend/modules/`: engine analisis CV, OCR, NLP, database helper lama, dan test kontrak.
- `backend/database/schema.sql`: schema PostgreSQL.
- `render.yaml`: contoh konfigurasi deployment full-stack.

## Menjalankan Lokal

Install dependency Node:

```powershell
npm install
```

Siapkan PostgreSQL dan file environment:

```powershell
Copy-Item backend\.env.example backend\.env
```

Isi minimal:

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
JOBFIT_ENABLE_GEMINI=false
JOBFIT_ENABLE_SEMANTIC_MODEL=false
```

Import dataset jobs ke PostgreSQL:

```powershell
cd backend
python scripts/import_jobs_to_postgres.py
cd ..
```

Jalankan API Express:

```powershell
npm run server
```

Jalankan frontend Vite di terminal kedua:

```powershell
npm run dev
```

Buka:

```text
http://127.0.0.1:4173/
```

Frontend lokal otomatis mengirim request ke:

```text
http://127.0.0.1:5000
```

Jika API berada di URL lain, set dari browser console:

```js
localStorage.setItem("jobfitApiBaseUrl", "https://api-jobfit.example.com")
```

## Build dan Production

Build frontend:

```powershell
npm run build
```

Jalankan production-like server:

```powershell
$env:APP_ENV="production"
$env:HOST="127.0.0.1"
npm start
```

Pada production, Express akan melayani REST API dan file statis dari `dist`.

## Deployment

Opsi paling sederhana adalah single-service deploy ke Render/Railway:

- Build command:
  `npm install && npm run build && python -m pip install -r backend/requirements.txt -t .codex-python-packages`
- Start command:
  `npm start`
- Environment minimal:
  `APP_ENV=production`, `HOST=0.0.0.0`, `DATABASE_URL`, `SMTP_HOST`, `SMTP_FROM` atau `SMTP_USER`, `SMTP_PASSWORD` jika memakai `SMTP_USER`, `JOBFIT_ENABLE_GEMINI=false`, dan `JOBFIT_ENABLE_SEMANTIC_MODEL=false`.

## Catatan Kepatuhan AI Dicoding

JobFit menggunakan sistem rekomendasi deterministik dan explainable:

- Rule-based requirement parser untuk skill wajib, skill pendukung, seniority, dan domain.
- BM25/IDF lokal dari dataset lowongan sendiri untuk corpus relevance.
- Taxonomy role dan synonym lokal untuk membedakan role seperti frontend, backend, data, admin, finance, design, culinary, dan lainnya.
- Course/project recommendation memakai database aturan lokal (`SAFE_RECOMMENDATION_DATABASE`), bukan API eksternal.

Sistem rekomendasi pekerjaan tidak menggunakan TensorFlow Hub, layanan API seperti ChatGPT/Gemini/OpenAI, AutoML, atau model pretrained untuk proses matching diskriminatif.

Jika frontend dipisah ke Netlify/Vercel, deploy hasil `npm run build`, lalu arahkan `jobfitApiBaseUrl` ke URL Express API.

## Kontrak API

Endpoint auth:

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

Endpoint analisis:

```text
GET /api/analyses
GET /api/analyses/titles?q=frontend
GET /api/analyses/:id
POST /api/analyses
```

Upload CV:

```text
POST /api/analyses
Content-Type: multipart/form-data

fields:
- cv: File PDF maksimal 5 MB
- targetRole: string
- analysisMode: targeted | auto
```

Jika request memakai token valid, hasil analisis disimpan ke tabel `analyses`. File PDF mentah tidak disimpan permanen.

## Validasi

Build frontend:

```powershell
npm run build
```

Cek Express syntax:

```powershell
node --check server.js
```

Cek API:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/health
```

Jalankan test Python penting:

```powershell
python backend\modules\test_api_contract.py
python backend\modules\test_database_contract.py
python backend\modules\test_frontend_hosting_contract.py
python backend\modules\test_security_hardening.py
python backend\modules\test_recommendation_evaluation.py
```

## Catatan Keamanan

- `backend/.env` berisi credential lokal dan sudah di-ignore oleh git.
- Jangan commit `.env`, `node_modules`, `dist`, atau cache Python.
- Rotate API key/SMTP password jika pernah terlihat di terminal, screenshot, atau repository publik.
