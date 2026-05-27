# JobFit - Data Scientist Handoff

Paket ini berisi kode dan dataset yang paling relevan untuk jobdesk Data Scientist.

## Fokus Tanggung Jawab
- Menjaga kualitas dataset lowongan kerja.
- Melakukan cleaning dan preprocessing dataset job.
- Mengevaluasi hasil skill extraction dan missing skills.
- Mengevaluasi logika match score dari sisi data.
- Menyiapkan dataset ke PostgreSQL.

## File Penting
- `backend/data/jobs_clean.csv`: dataset utama lowongan kerja.
- `backend/data/extracted_cv_data.csv`: dataset hasil ekstraksi CV.
- `backend/modules/preprocess_jobs.py`: preprocessing dataset job.
- `backend/modules/data_loader.py`: loader dataset dari CSV/PostgreSQL.
- `backend/modules/cv_loader.py`: loader data CV.
- `backend/modules/matching.py`: referensi dasar perhitungan skill match.
- `backend/modules/nlp.py`: skill list, sinonim, dan education/domain mapping yang perlu dievaluasi.
- `backend/database/schema.sql`: schema PostgreSQL tabel `jobs`.
- `backend/scripts/import_jobs_to_postgres.py`: import dataset job ke PostgreSQL.
- `backend/scripts/check_postgres_jobs.py`: cek koneksi dan jumlah data PostgreSQL.
- `backend/scripts/setup-postgres.ps1`: setup otomatis database lokal.

## Catatan Dataset
- Dataset job saat ini berisi kolom:
  `job_no`, `title`, `company`, `location`, `keyword`, `job_url`, `description`, `scraped_at`, `fingerprint`.
- `fingerprint` dipakai untuk mencegah data duplikat saat import ulang.
- File cache generated `processed_jobs_cache.json` sengaja tidak dimasukkan ke zip karena bisa dibuat ulang oleh backend.

## Cara Import Dataset
```powershell
cd backend
python scripts/import_jobs_to_postgres.py
python scripts/check_postgres_jobs.py
```

Pastikan `backend/.env` sudah berisi `DATABASE_URL`, `JOBS_SOURCE=postgres`, dan `JOBS_TABLE=jobs`.

