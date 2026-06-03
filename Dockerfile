# Gunakan image resmi yang sudah menggabungkan Python 3.11 dan Node.js 20
FROM nikolaik/python-nodejs:python3.11-nodejs20

# Tentukan direktori kerja di dalam container
WORKDIR /app

# Copy package.json dan package-lock.json terlebih dahulu untuk memanfaatkan cache layer Docker
COPY package*.json ./

# Install semua dependensi Node.js karena proses build Vite membutuhkan devDependencies
RUN npm install

# Copy requirements.txt dari backend
COPY backend/requirements.txt ./backend/

# Install dependensi Python menggunakan pip
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

# Copy seluruh kode proyek ke dalam container
COPY . .

# Build frontend asset Vite menjadi file statis agar bisa langsung di-serve oleh Express di production
RUN npm run build && npm prune --omit=dev

# Set environment variables untuk production
ENV NODE_ENV=production
ENV APP_ENV=production
ENV HOST=0.0.0.0
ENV PORT=7860
ENV PYTHON_PATH=python
ENV PYTHON_ANALYSIS_TIMEOUT_MS=90000
ENV MAX_CANDIDATE_JOBS=150
ENV AUTO_MAX_CANDIDATE_JOBS=120
ENV JOBFIT_ENABLE_GEMINI=false
ENV JOBFIT_ENABLE_SEMANTIC_MODEL=false

# Expose port (7860 adalah port standar yang wajib digunakan oleh Hugging Face Spaces)
EXPOSE 7860

# Jalankan server Express Node.js
CMD ["node", "server.js"]
