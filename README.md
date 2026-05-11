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

```bash
node static-server.js
```

Lalu buka:

```text
http://127.0.0.1:4173/
```

## Simulasi API

Halaman upload mensimulasikan alur:

```text
POST /api/analyses
Content-Type: multipart/form-data

fields:
- cv: File PDF
- targetRole: string
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
