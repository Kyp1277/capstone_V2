# 🔍 Laporan Audit & Analisis Komponen JobFit — Versi 1.2

Laporan ini menyajikan hasil pemeriksaan mendalam terhadap **JobFit**, sebuah aplikasi web prototype *AI-powered CV Match Analyzer* yang dirancang untuk membantu pencari kerja mengunggah CV (PDF), menganalisis keselarasan skill dengan lowongan target, serta merekomendasikan lowongan terdekat dari dataset berisi **~10.785 lowongan pekerjaan**.

---

## 🏗️ Gambaran Arsitektur Sistem saat Ini

Aplikasi JobFit terdiri dari tiga komponen utama yang terintegrasi secara modular:

```mermaid
flowchart TB
    subgraph Frontend "Frontend (SPA Statis)"
        HTML["index.html\n(Entry point)"]
        CSS["styles.css\n(HSL Design & Dark Mode)"]
        Router["router.js\n(Custom Hash Router)"]
        State["state.js\n(Global State & Session)"]
        Canvas["dashboard.js\n(Manual Radar Chart Canvas)"]
    end

    subgraph Backend "Backend (FastAPI)"
        API["api.py\n(FastAPI Server)"]
        Auth["auth_service.py\n(OTP, Session, PBKDF2)"]
        DB["database.py\n(PostgreSQL Connection & Schema)"]
        Jobs["jobs_service.py\n(Cache & Prep jobs)"]
    end

    subgraph AIEngine "AI Engine (Modules)"
        Parser["cv_parser.py\n(pdfplumber extraction)"]
        NLP["nlp.py\n(Weighted Skill & Exp Parser)"]
        Score["analysis_service.py\n(Hybrid Scoring & Prefilter)"]
        Transformers["sentence-transformers\n(paraphrase-multilingual-MiniLM-L12-v2)"]
    end

    HTML --> Router --> State
    Router --> Canvas
    State --> API
    API --> Auth --> DB
    API --> Score
    Score --> Parser --> NLP
    Score --> Transformers
```

---

## ✅ Kelebihan Utama (Strengths)

Berdasarkan pemeriksaan mendalam terhadap kode sumber versi **1.2**, sistem ini memiliki fondasi teknis dan arsitektur yang sangat luar biasa untuk level Capstone Project:

### 1. Desain Frontend SPA Statis yang Sangat Premium & Estetik
- **Desain HSL Modern & Adaptif**: Sistem styling di `styles.css` memanfaatkan variabel warna HSL yang dikurasi dengan sangat baik. Skema warna *Light Mode* dan *Dark Mode* terlihat sangat harmonis, modern, dan memberikan impresi kelas atas.
- **Interaksi & Mikro-Animasi Halus**: UI didukung dengan animasi *sheen effect* pada tombol utama, *floating effects*, *fade-up*, dan *breathe ring* yang membuat visual terasa hidup dan interaktif.
- **Visualisasi Grafik Radar Canvas Kustom**: Di `dashboard.js`, visualisasi *radar chart* untuk pemisahan skor kecocokan CV (*breakdown score*) digambar secara manual di atas elemen `<canvas>` HTML5 dengan pengaturan posisi teks dinamis guna mencegah *clipping* pada resolusi layar yang berbeda.
- **State Management & Router Mandiri**: Penggunaan sistem hash router (`#/upload`, `#/dashboard`) dan pemusatan data UI global di `js/state.js` membuat aplikasi web statis ini berjalan mulus tanpa reload halaman, sehingga sangat cocok dideploy di hosting statis (seperti GitHub Pages atau Vercel).

### 2. Pipeline AI Hybrid Multi-Signal yang Canggih
Model pencocokan di `analysis_service.py` tidak hanya membandingkan teks secara kasar, melainkan menggabungkan **5 sinyal terpisah** dengan formula bobot tertata:
- **Skill Match (40%)**: Menghitung irisan skill menggunakan bobot frekuensi kemunculan skill ditambah context bonus.
- **Role Match (20%)**: Menilai relevansi target role pengguna dengan judul dan deskripsi lowongan kerja.
- **Semantic Similarity (15%)**: Menggunakan kedekatan makna dari model embedding transformer.
- **Transferable Score (10%)**: Menilai kesamaan token secara luas untuk sinyal pendukung.
- **Education Match (15%)**: Mengecek kecocokan bidang studi akademik dan tingkat pendidikan.

### 3. Peningkatan Skalabilitas & Dukungan Bilingual (Bilingual & Scaling)
- **Model Semantik Multibahasa**: Peningkatan menggunakan model `paraphrase-multilingual-MiniLM-L12-v2` yang mendukung lebih dari 50 bahasa (termasuk Bahasa Indonesia dan Inggris) membuat pencocokan pada CV bilingual (campuran ID-EN) menjadi jauh lebih akurat dibandingkan model monolingual English biasa.
- **Pra-Penyaringan Kandidat (Candidate Pre-filtering)**: Untuk mengatasi pencarian di dataset berukuran ~10.785 lowongan tanpa menurunkan performa, sistem menerapkan *pre-filtering* cepat menggunakan formula statistik ringan untuk memotong dataset ke pool berisi `MAX_CANDIDATE_JOBS=250` pekerjaan terbaik sebelum diproses oleh model semantik transformer yang berat. Ini memotong load komputasi hingga **98%**.

### 4. Proteksi Server & Pengoptimalan Kinerja (Production Hardening)
- **Caching Embedding Semantik**: Hasil komputasi vektor (*embedding*) deskripsi lowongan disimpan sementara di `_JOB_EMBEDDING_CACHE` dalam memori server, sehingga deskripsi pekerjaan yang sama tidak perlu di-encode berulang kali untuk setiap request analisis pengguna.
- **Kontrol Konkurensi dengan Semaphore**: Diterapkan `_SEMANTIC_SEMAPHORE = Semaphore(2)` untuk membatasi pemanggilan proses pengodean model secara bersamaan, melindungi server dengan spesifikasi memori terbatas agar tidak mengalami kehabisan RAM (*memory pressure*).
- **Penanganan Stopwords Terperinci**: Kumpulan stopwords di `jobs_service.py` telah diperluas mencakup 32 kata umum bahasa Indonesia dan 32 kata umum bahasa Inggris untuk meningkatkan akurasi ekstraksi token.
- **Pendidikan & Pengalaman Kerja Lebih Pintar**: Sistem pendeteksi pengalaman kerja di `nlp.py` telah dilengkapi filter cerdas seperti penanganan *stop headers* (agar bagian Pendidikan/Keahlian tidak tersedot sebagai pengalaman kerja), verifikasi rentang tahun (menghindari tahun versi perangkat lunak dibaca sebagai durasi kerja), serta deteksi tingkat gelar (S2/S3 mendapatkan skor bonus, sedangkan SMA/SMK disesuaikan).
- **Rekomendasi yang Dipersonalisasi**: Sistem tidak lagi sekadar menggunakan template statis, melainkan menghasilkan tips perbaikan CV (`build_improvements`) berdasarkan skill gap nyata dan analisis tingkat kepercayaan (*confidence weight*) skill terdeteksi.

### 5. Keamanan & Manajemen Database yang Tangguh
- **Keamanan Kredensial**: Hashing password menggunakan algoritma industri standar `PBKDF2-SHA256` dengan 210.000 iterasi. Token sesi di-hash kembali di database menggunakan SHA-256 untuk memitigasi pencurian data sesi langsung dari database.
- **Skema & Otomasi PostgreSQL**: Integrasi penuh menggunakan adapter PostgreSQL modern `psycopg` lengkap dengan pembuatan skema relasional otomatis, indeks pencarian pada kolom kunci, dan pembersihan otomatis sesi kedaluwarsa.
- **Test Harness yang Sangat Lengkap**: Tersedia skrip validasi komprehensif mulai dari unit test parser PDF, database contract test, API response contract, hingga evaluasi kualitas algoritma rekomendasi (`test_recommendation_evaluation.py`) menggunakan synthetic CV.

---

## ❌ Kelemahan & Batasan Saat Ini (Weaknesses)

Meskipun fondasi proyek V1.2 ini sudah sangat matang dan teroptimasi, masih terdapat beberapa kelemahan alami (*inherent limitations*) yang patut dicermati:

### 1. Ekstraksi Skill Murni Berbasis Kamus & Regex (Dictionary-Based Extraction)
- **Toleransi Typo Rendah**: Skill dicocokkan secara eksak menggunakan kompilasi pola regex regex dari `SKILL_LIST` dan `SKILL_SYNONYMS`. Jika pelamar mengetik typo kecil di CV (misalnya: `"Phyton"`, `"Javascripts"`, `"Nodjs"`), skill tersebut tidak akan terdeteksi sama sekali.
- **Ketergantungan Pembaruan Manual**: Teknologi berkembang dengan sangat cepat. Jika ada pustaka baru yang belum terdaftar di `SKILL_LIST` (misalnya: *"Next.js"*, *"Supabase"*, *"Terraform"*), maka sistem tidak akan dapat mengenalinya sebelum daftar kamus diperbarui secara manual di dalam kode program.
- **Skalabilitas Kamus Lintas Domain**: Kamus skill saat ini sangat dominan pada domain IT/Software. Domain pekerjaan non-IT (seperti pariwisata, kuliner, hukum, medis) memiliki representasi daftar skill yang relatif lebih sedikit di database kamus.

### 2. Ketiadaan Parser Gambar OCR Fallback
- **Masalah pada CV Hasil Scan**: Parser di `cv_parser.py` murni mengandalkan pustaka `pdfplumber` untuk mengekstrak layer teks PDF. Banyak pencari kerja (terutama pelamar pemula atau fresh graduate) yang mengekspor CV mereka dalam format dokumen pindaian (*scanned image*) atau membuat desain CV berbasis gambar raster murni. Dokumen jenis ini akan menghasilkan string teks kosong saat dibaca oleh parser, menyebabkan Match Score langsung jatuh ke **0%** disertai peringatan kualitas dokumen.

### 3. Pemrosesan Parser Pengalaman Kerja Masih Relatif Kaku (Rule-Based Parsing)
- **Format Dokumen Tidak Standar**: Meskipun parser pengalaman di `nlp.py` sudah sangat dikuatkan menggunakan pembatas sub-bagian, ia tetap mengasumsikan pola penulisan yang linier per baris (seperti `"Jabatan - Perusahaan"` atau `"Nama Jabatan ... Tanggal"`). CV yang dirancang dengan layout multi-kolom yang kompleks atau memiliki struktur tabel sering kali membuat pemisah baris teks tercampur aduk ketika dibaca oleh `pdfplumber`, sehingga ekstraksi pengalaman kerja berpotensi gagal mengurai rentang tahun atau nama instansi dengan sempurna.

### 4. Cache Semantik yang Bersifat Sementara (Transient Memory Cache)
- **Restart Server Menghapus Cache**: Penyimpanan vektor embedding lowongan pekerjaan di `_JOB_EMBEDDING_CACHE` murni berupa variabel in-memory global (*dictionary* Python). Setiap kali server backend FastAPI dimulai ulang (*restart* atau *crash*), cache embedding ini akan terhapus sepenuhnya. Akibatnya, request analisis CV pertama setelah restart akan memakan waktu komputasi yang lambat karena harus memproses ulang embedding vektor deskripsi lowongan dari awal.

---

## 🚀 Peluang Pengembangan Lebih Lanjut (Future Roadmap)

Untuk membawa aplikasi prototype JobFit ini ke tingkat komersial (*production-ready enterprise application*), beberapa langkah pengembangan lanjutan berikut sangat disarankan:

### 1. Penerapan Pencocokan Fuzzy untuk Deteksi Skill (Fuzzy Match Integration)
Integrasikan pustaka pencarian teks berbasis kemiripan string seperti `rapidfuzz` atau algoritma Levenshtein distance pada fase ekstraksi skill:
- **Solusi Typo**: Ketika mendeteksi token, bandingkan dengan entri terdekat di kamus skill. Jika kemiripan kata di atas **90%** (misalnya `"Phyton"` ke `"Python"`), catat sebagai kecocokan valid dengan penyesuaian bobot (*confidence*) sedikit diturunkan.

### 2. Integrasi OCR Fallback (Optical Character Recognition)
Tambahkan pustaka deteksi teks berbasis gambar dalam pipeline CV parser:
- **Alur Fallback**: Jika hasil ekstraksi teks teks awal dari `pdfplumber` menghasilkan panjang teks kurang dari batas minimum (`MIN_EXTRACTED_TEXT_LENGTH`), otomatis alihkan parser untuk memproses dokumen PDF halaman demi halaman menjadi citra gambar, lalu jalankan pustaka OCR open-source seperti `pytesseract` atau `easyocr` untuk mengekstrak layer teksnya sebelum dialirkan ke modul NLP.

### 3. Pengolahan Data Menggunakan NLP Berbasis LLM / NER (Named Entity Recognition)
Beralih dari deteksi skill berbasis kamus regex ke model berbasis ekstraksi struktural:
- **Deep Learning NER**: Gunakan model pemrosesan bahasa alami berukuran kecil (seperti SpaCy yang di-finetune untuk resume bahasa Indonesia) untuk melabeli entitas bernama seperti `SKILL`, `JOB_TITLE`, `ORGANIZATION`, dan `EDUCATION` secara kontekstual tanpa perlu mendaftarkan setiap kosakata skill baru.
- **LLM Agent Pipeline (Gemini API / Gemini 3.5 Flash)**: Mengingat ketersediaan runtime yang kuat saat ini, sistem dapat mengintegrasikan API Gemini untuk melakukan ekstraksi JSON struktural dari teks mentah CV secara instan. LLM dapat mengidentifikasi riwayat pengalaman yang kompleks, menerjemahkan bahasa secara otomatis dengan pemahaman nuansa semantik HR yang sangat tinggi, serta menghasilkan rekomendasi perbaikan CV (*Action Plan*) yang sangat manusiawi, terperinci, dan tidak kaku.

### 4. Penyimpanan Embedding Vektor dengan Vector Database (pgvector Integration)
Untuk meningkatkan efisiensi pencarian kecocokan semantik di skala jutaan lowongan:
- **Penyimpanan Vektor Permanen**: Gunakan ekstensi `pgvector` di PostgreSQL yang sudah terinstall di database lokal.
- **Alur Kerja**: Saat lowongan pekerjaan baru dimasukkan ke database, segera hitung embedding deskripsi lowongan tersebut menggunakan Sentence-Transformers secara asinkron, lalu simpan representasi vektornya langsung ke kolom database tipe data `VECTOR`. Ketika pengguna mengunggah CV, sistem hanya perlu menghitung embedding teks CV sebanyak **1 kali saja** di backend, kemudian melakukan pencarian jarak kosinus langsung lewat kueri SQL (`ORDER BY embedding <=> user_cv_embedding LIMIT 250`). Ini akan mengeliminasi kebutuhan in-memory cache sepenuhnya dan mempercepat waktu respons hingga di bawah **100 milidetik**.

---

## 📈 Kesimpulan Audit

Proyek **JobFit Versi 1.2** adalah sebuah aplikasi capstone yang memiliki **kualitas kode sangat tinggi, rapi, dan terstruktur secara profesional**. 

Kelebihan utamanya terletak pada **arsitektur SPA statis frontend yang sangat premium dan estetik**, dipadukan dengan backend FastAPI berbasis PostgreSQL yang **aman (PBKDF2, SHA-256 session token), tangguh (concurrency semaphore, caching embedding), serta memiliki pipeline scoring hybrid multibahasa yang sangat cerdas**.

Batasan sistem yang ada saat ini (regex skill, tiadanya OCR, in-memory cache) adalah batasan teknis wajar pada fase pengembangan prototipe. Arah pengembangan terbaik berikutnya adalah mengintegrasikan **Fuzzy Matching**, **OCR Fallback**, serta mengimplementasikan **Gemini API / pgvector** untuk menghadirkan skalabilitas dan kecerdasan tingkat lanjut yang siap bersaing di pasar industri.
