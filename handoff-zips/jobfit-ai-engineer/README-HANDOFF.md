# JobFit - AI Engineer Handoff

Paket ini berisi kode yang paling relevan untuk jobdesk AI Engineer.

## Fokus Tanggung Jawab
- Mengembangkan NLP untuk ekstraksi skill dari CV.
- Mengembangkan weighted skill extraction.
- Mengembangkan matching algorithm, semantic similarity, dan recommendation reasoning.
- Menjaga parser CV tetap memakai `pdfplumber`.
- Mengoptimasi akurasi dan performa rekomendasi pekerjaan.

## File Penting
- `backend/api.py`: pipeline analisis CV, scoring, candidate filtering, dan response API.
- `backend/modules/nlp.py`: skill database, sinonim, weighted skill extraction, education/major detection, domain mapping.
- `backend/modules/cv_parser.py`: pembaca PDF memakai `pdfplumber`.
- `backend/modules/semantic.py`: referensi semantic similarity berbasis sentence-transformers.
- `backend/modules/matching.py`: referensi dasar skill matching.
- `backend/modules/recomendation.py`: referensi recommendation engine lama.
- `backend/modules/data_loader.py`: loader dataset dari CSV/PostgreSQL agar pipeline AI bisa dijalankan.
- `backend/requirements.txt`: dependency backend.

## Catatan Algoritma Terbaru
- Skill CV sudah berbobot berdasarkan frekuensi dan konteks.
- Sinonim seperti `js`, `ms excel`, `ml`, dan `ui/ux` tetap dinormalisasi.
- Candidate filtering dilakukan sebelum semantic similarity agar tidak menghitung semua dataset job.
- Pendidikan/jurusan ikut dipertimbangkan melalui `educationMatch`.
- Frontend contract belum berubah, jadi response lama tetap aman.

## Cara Coba Lokal
```powershell
cd backend
python api.py
```

Endpoint utama:
```text
POST /api/analyses
GET /health
```

