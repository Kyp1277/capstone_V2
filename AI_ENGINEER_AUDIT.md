# Audit Kesesuaian JobFit AI Engineer

Tanggal audit: 23 Mei 2026

## Ringkasan Keputusan

Paket `jobfit-ai-engineer_rev.zip` dinilai **sudah sesuai secara struktur dan test dasar** dengan target jobdesk AI Engineer yang tertulis di `README-HANDOFF.md`.

Catatan penting: artefak yang lolos adalah paket revisi zip v1.2. Folder lokal `D:\capstone dicoding\jobfit-ai-engineer` masih berisi versi lebih lama yang test-nya berjalan, tetapi ekstraksi pengalaman kerja masih noisy dan ikut menangkap baris pendidikan/skill sebagai pengalaman.

## Target AI Engineer Yang Dicek

- NLP untuk ekstraksi skill CV.
- Weighted skill extraction.
- Matching algorithm, semantic similarity, dan recommendation reasoning.
- Parser CV tetap memakai `pdfplumber`.
- Optimasi akurasi/performa rekomendasi pekerjaan melalui candidate filtering.

## Hasil Validasi Teknis

- `py_compile` untuk backend paket revisi: **lulus**.
- Test work experience assertion paket revisi: **lulus** dengan output akhir `ALL TESTS PASSED`.
- Parser PDF: **sesuai**, `backend/modules/cv_parser.py` memakai `pdfplumber.open()`.
- NLP: **sesuai**, `backend/modules/nlp.py` memiliki `SKILL_LIST`, `SKILL_SYNONYMS`, `extract_weighted_skills()`, `extract_education_profile()`, `infer_job_domains()`, dan `extract_work_experience()`.
- Work experience v1.2: **sesuai**, sudah memakai exact experience header, stop header, filter education line, filter skill-list line, dan validasi year range.
- Matching pipeline: **sesuai**, `backend/api.py` menghitung `skill_score`, `semantic_score`, `role_score`, `transfer_score`, `education_score`, missing skill penalty, candidate prefilter, dan final score.
- Recommendation reasoning: **sesuai**, setiap job card membawa `matchedSkills`, `missingSkills`, `detail`, `notFitReason`, `improvements`, dan `scoreBreakdown`.

## Kontrak API

Endpoint `POST /api/analyses` tetap kompatibel dengan response lama karena field utama masih ada:

- `id`
- `targetRole`
- `score`
- `detectedSkills`
- `missingSkills`
- `improvements`
- `jobs`

Field AI tambahan juga tersedia:

- `analysisMode`
- `verdict`
- `summary`
- `workExperiences`
- `totalExperienceYears`
- `experienceLevel`
- `experienceMatch`
- `jobs[].scoreBreakdown`
- `jobs[].matchedSkills`
- `jobs[].missingSkills`
- `jobs[].notFitReason`
- `jobs[].improvements`

## Bukti Perbandingan Versi

Versi lokal lama menunjukkan masalah pada test print-based: CV backend synthetic menghasilkan 8 pengalaman, termasuk baris seperti `S1 Teknik Informatika` dan daftar skill.

Versi zip revisi v1.2 memperbaiki hal tersebut:

- CV backend synthetic menghasilkan 3 pengalaman valid.
- CV HR synthetic menghasilkan 3 pengalaman valid.
- CV project manager synthetic menghasilkan 3 pengalaman valid.
- Negative test tanpa section experience menghasilkan list kosong.
- Negative test pendidikan/skill tidak lolos sebagai pengalaman kerja.

## Kesimpulan

Paket revisi `jobfit-ai-engineer_rev.zip` layak dinyatakan **sesuai untuk target AI Engineer pada level code structure, algorithm coverage, dan unit/synthetic validation**.

Belum bisa dinyatakan production-ready penuh sampai dilakukan uji end-to-end dengan dataset job nyata dan minimal dua CV nyata atau representatif: satu CV IT/software dan satu CV non-IT.

## Rekomendasi Lanjutan

- Gunakan paket zip v1.2 sebagai source of truth, bukan folder lokal lama.
- Sinkronkan isi zip ke folder kerja bila proyek akan dilanjutkan.
- Jalankan API dengan dataset nyata dan uji ranking rekomendasi lintas domain.
- Perbaiki dokumentasi path test karena changelog menyebut `backend/test_work_experience.py`, sedangkan paket revisi menaruh test di `backend/modules/test_work_experience.py`.
