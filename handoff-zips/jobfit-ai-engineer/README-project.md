# JobFit UI Prototype

JobFit adalah prototype UI/UX aplikasi web untuk analisis CV berbasis AI. Prototype ini dibuat sebagai frontend statis dengan hash routing agar bisa langsung dibuka di browser tanpa instalasi dependency.

## Halaman

- Landing Page: hero, fitur utama, cara kerja, dan CTA.
- Upload CV: drag and drop PDF, input target pekerjaan, state selected/loading/error.
- Dashboard Hasil: match score, ringkasan AI, detected skills, missing skills, rekomendasi CV, rekomendasi pekerjaan.
- Riwayat Analisis: daftar analisis yang siap dihubungkan ke database.
- 404 Page: fallback route untuk halaman tidak ditemukan.

## Struktur

- `index.html`: entry point aplikasi.
- `styles.css`: style guide, layout responsive, komponen UI.
- `app.js`: hash router, mock state, simulasi networking call, dan interaksi UI.
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

Jika menjalankan backend dengan Python manual:

```powershell
cd backend
pip install -r requirements.txt
python api.py
```

## Dataset PostgreSQL

Backend bisa membaca dataset lowongan dari PostgreSQL. Jika `DATABASE_URL` diisi, backend otomatis memakai PostgreSQL; jika tidak, backend tetap memakai `backend/data/jobs_clean.csv`.

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

Endpoint `/health` akan menampilkan `jobsSource` dan jumlah data yang dibaca. Untuk memaksa kembali ke CSV:

```powershell
$env:JOBS_SOURCE="csv"
```

Frontend membaca status tersebut dari `/health`. Jika database aktif, status bar akan menampilkan jumlah dataset job dari PostgreSQL.

## Kontrak API

Halaman upload mengirim request ke backend:

```text
POST /api/analyses
Content-Type: multipart/form-data

fields:
- cv: File PDF
- targetRole: string
- analysisMode: targeted | auto
```

Response yang diharapkan untuk implementasi full-stack:

```json
{
  "id": "analysis-001",
  "targetRole": "Frontend Developer",
  "score": 82,
  "detectedSkills": ["HTML", "CSS", "JavaScript", "React"],
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

Untuk mencoba error state, isi target pekerjaan dengan kata `error`, pilih PDF, lalu klik `Analisis Sekarang`.
