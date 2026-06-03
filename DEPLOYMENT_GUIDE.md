# 🚀 Panduan Deployment JobFit - Fullstack & Database (100% Gratis & Gacor)

Dokumen ini menjelaskan langkah-langkah praktis untuk men-deploy aplikasi **JobFit** (Frontend Vite + Backend Express Node.js + Engine Python ML + PostgreSQL) secara gratis dengan spesifikasi tinggi tanpa terkena *Out of Memory (OOM)*.

---

## 🏆 Opsi Utama: Hugging Face Spaces (Docker Space) - *Rekomendasi Utama (RAM 16GB!)*

Karena sistem JobFit menggunakan modul machine learning Python (`sentence-transformers`, `easyocr`, dll.) yang membutuhkan RAM cukup besar (minimal 1GB - 1.5GB saat memuat model PyTorch), men-deploy di **Render Free Tier** (512MB RAM) sering kali memicu **OOM (Out Of Memory) Crash (Exit Code 137)**.

**Hugging Face Spaces** menyediakan container Docker gratis dengan spesifikasi luar biasa:
* **RAM: 16 GB** (Sangat lancar untuk AI/ML)
* **vCPU: 2 Cores**
* **Biaya: 100% GRATIS 24/7**

### Langkah-Langkah Deploy di Hugging Face Spaces:
1. Buat akun di [Hugging Face](https://huggingface.co/).
2. Klik tombol **New** -> **Space** di kanan atas.
3. Konfigurasikan Space baru Anda:
   * **Space name**: `jobfit-analyzer` (atau sesuka Anda)
   * **SDK**: Pilih **Docker** (Ini sangat penting! Pilih opsi *Blank*).
   * **Space License**: `apache-2.0` (bebas)
   * **Visibility**: **Public** (agar bisa diakses umum).
4. Klik **Create Space**.
5. Setelah Space terbuat, Anda akan mendapatkan alamat repositori Git untuk Space tersebut.
6. Hubungkan repositori GitHub lokal Anda atau push kode langsung ke repositori Git Hugging Face tersebut. Karena di repositori Anda sudah ada file `Dockerfile` kustom yang saya buatkan, Hugging Face akan mendeteksi dan melakukan build otomatis secara langsung!
7. Masuk ke tab **Settings** di Space Anda, lalu tambahkan variabel lingkungan (**Variables and secrets**) yang dibutuhkan aplikasi (samakan dengan isi `.env` Anda):
   * `DATABASE_URL` = *(Tautan koneksi PostgreSQL Anda dari Neon/Supabase)*
   * `JOBS_SOURCE` = `postgres`
   * `JOBS_TABLE` = `jobs`
   * `APP_ENV` = `production`
   * `GEMINI_API_KEY` = *(Kunci API Gemini Anda)*
   * `RESEND_API_KEY` = *(Disarankan untuk Hugging Face Spaces karena SMTP 587/465 dapat diblokir)*
   * `EMAIL_FROM` = `JobFit <onboarding@resend.dev>` *(atau domain email Anda yang sudah diverifikasi di Resend)*
   * `SMTP_HOST` = *(Opsional fallback jika deploy di platform yang mendukung SMTP)*
   * ... dst.

---

## 💾 Layanan PostgreSQL Gratis & Performa Tinggi

Untuk database PostgreSQL, jangan gunakan database bawaan lokal. Gunakan penyedia PostgreSQL cloud gratis berikut:

### 1. Neon.tech (Sangat Direkomendasikan 🌟)
* **Spesifikasi**: 1 Project, database PostgreSQL serverless gratis, limit storage 0.5 GB (sangat cukup untuk ribuan baris lowongan kerja).
* **Cara Daftar**:
  1. Masuk ke [neon.tech](https://neon.tech/) dan daftar dengan akun GitHub Anda.
  2. Buat project baru bernama `jobfit`.
  3. Salin **Connection String** yang diberikan (biasanya berbentuk `postgresql://alex:password@ep-cool-shadow-123456.us-east-2.aws.neon.tech/neondb?sslmode=require`).
  4. Gunakan URL tersebut sebagai nilai `DATABASE_URL` di konfigurasi environment backend Anda.

### 2. Supabase
* **Spesifikasi**: Menyediakan database PostgreSQL gratis dengan kapasitas yang cukup besar.
* **Cara Daftar**: Buat project baru di [supabase.com](https://supabase.com/), masuk ke menu **Database Settings**, lalu ambil URI koneksi PostgreSQL langsung.

---

## ⚡ Opsi Alternatif: Render (Docker/Node Web Service)

Jika Anda tetap ingin menggunakan Render:
1. Daftarkan akun di [render.com](https://render.com/).
2. Buat **New Web Service**, sambungkan repositori GitHub Anda.
3. Pilih runtime **Docker** (bukan Node), karena file `Dockerfile` kita akan mengonfigurasi Node dan Python sekaligus secara otomatis.
4. Pilih plan **Free**.
5. Masukkan Environment Variables di dashboard Render.
6. *Catatan*: Jika aplikasi mengalami crash karena kehabisan RAM (OOM), Anda harus mengoptimalkan penggunaan memori dengan meminimalkan ukuran model ML lokal atau beralih sepenuhnya ke API Gemini untuk proses pemetaan.
