# Data Dictionary - Dataset Lowongan Kerja JobFit

Dokumen ini menyediakan spesifikasi terperinci mengenai dataset lowongan kerja (`jobs_clean.csv`) yang digunakan dalam proyek **JobFit - AI CV Match Analyzer**. Dataset ini merupakan inti data untuk pencarian lowongan kerja, visualisasi statistik, serta dasar pencocokan berbasis kecerdasan buatan (AI CV Matcher).

---

## 📊 Ringkasan Dataset
* **Nama File**: `jobs_clean.csv`
* **Format**: Comma-Separated Values (CSV)
* **Ukuran File**: ± 14.5 MB
* **Jumlah Kolom**: 9 kolom utama
* **Fungsi Utama**: Menyimpan metadata lowongan pekerjaan hasil proses *gathering* dan *cleaning* untuk digunakan oleh API server dan engine pencocokan skill (NLP).

---

## 🗂️ Kamus Data (Data Dictionary)

| Nama Kolom | Tipe Data | Deskripsi | Aturan & Keterangan | Contoh Data |
| :--- | :--- | :--- | :--- | :--- |
| **`job_no`** | `INTEGER` | Identifikasi unik (Primary Key) untuk setiap baris lowongan pekerjaan. | Harus bertipe angka urut, tidak boleh berisi nilai kosong (*NULL*) atau duplikat. | `1`, `42`, `108` |
| **`title`** | `VARCHAR` | Nama atau judul posisi lowongan pekerjaan yang ditawarkan. | Berisi teks alfabetis, disingkat secara formal (misalnya: *Frontend Developer*, *Data Scientist*). | `Data Analyst`, `Software Engineer` |
| **`company`** | `VARCHAR` | Nama perusahaan atau instansi yang membuka lowongan pekerjaan. | Berisi nama resmi korporasi/organisasi. Diisi `Unknown` jika tidak terdeteksi. | `Gojek`, `Shopee`, `Unknown` |
| **`location`** | `VARCHAR` | Lokasi fisik atau penempatan kerja posisi lowongan tersebut. | Menyebutkan kota dan negara, atau berstatus `Remote` untuk kerja jarak jauh. | `Jakarta, Indonesia`, `Remote` |
| **`keyword`** | `VARCHAR` | Kata kunci/kategori industri yang mewakili klaster lowongan kerja. | Digunakan untuk filter pencarian cepat dan pengelompokan domain peran. | `Data Science`, `IT`, `Marketing` |
| **`job_url`** | `VARCHAR` | Tautan URL asli asal lowongan pekerjaan dikumpulkan. | Harus berformat URL valid (`http://` atau `https://`). | `https://linkedin.com/jobs/view/...` |
| **`description`** | `TEXT` | Deskripsi detail lowongan kerja, kualifikasi, deskripsi tugas, dan keahlian yang dibutuhkan. | Berisi teks paragraf panjang dengan list bullet. Menjadi sumber ekstraksi keahlian (*required skills*) oleh AI. | `Memiliki keahlian Python, SQL, dan Tableau...` |
| **`scraped_at`** | `TIMESTAMP` | Waktu/tanggal data lowongan dikumpulkan oleh sistem crawler/scraper. | Berformat ISO 8601 (`YYYY-MM-DD HH:MM:SS`). | `2026-05-15 08:30:12` |
| **`fingerprint`** | `VARCHAR(64)`| Hasil enkripsi (hash md5/sha256) unik berdasarkan gabungan konten lowongan. | Digunakan untuk mendeteksi dan mengeliminasi data duplikat secara efisien (*de-duplication*). | `7a9b8c6d4e2f1a0b3c...` |

---

## 🧹 Kebijakan Pembersihan Data (Data Cleaning Policy)
1. **Handling Missing Values**: Kolom bertipe teks yang bernilai kosong otomatis dikonversi menjadi string `'Unknown'` melalui fungsi pengolahan data.
2. **De-duplikasi**: Setiap baris data divalidasi menggunakan kolom `fingerprint` (kombinasi `title` + `company` + `description`). Data dengan `fingerprint` yang sama akan dihapus secara otomatis demi menjaga integritas statistik.
3. **Normalisasi Whitespace**: Karakter spasi ganda, baris baru yang berlebihan, serta karakter khusus hasil scraping dibersihkan agar teks deskripsi rapi dan siap diproses oleh modul Natural Language Processing (NLP).
