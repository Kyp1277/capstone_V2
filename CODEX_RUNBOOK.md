# Codex Runbook - JobFit

Panduan singkat ini dibuat supaya sesi Codex berikutnya tidak perlu meraba-raba cara menjalankan project.

## Lokasi Project

```text
D:\capstone dicoding
```

Backend utama:

```text
D:\capstone dicoding\backend
```

Frontend statis:

```text
D:\capstone dicoding
```

## Runtime Yang Aman Dipakai

Di environment ini command `python` tidak selalu tersedia di PATH. Gunakan Python bawaan Codex:

```text
C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

Node.js bawaan Codex:

```text
C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
```

## Menjalankan Backend

Backend memakai FastAPI dan listen di:

```text
http://127.0.0.1:5000
```

Command manual:

```powershell
cd "D:\capstone dicoding\backend"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" api.py
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5000/health"
```

Expected:

```text
status: ok
jobsLoaded: 10785
jobsSource: postgres
```

## Menjalankan Frontend

Frontend memakai static server kecil di:

```text
http://127.0.0.1:4173/
```

Command manual:

```powershell
cd "D:\capstone dicoding"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" static-server.js
```

Static server otomatis proxy request `/api/*` dan `/health` ke backend:

```text
http://127.0.0.1:5000
```

## Menjalankan Keduanya Untuk Browser User

Jika user ingin membuka dari browser Windows, proses perlu hidup di luar sandbox. Gunakan request escalation dan jalankan:

```powershell
$root = "D:\capstone dicoding"
$python = "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$node = "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$backend = Join-Path $root "backend"
Start-Process -FilePath $python -ArgumentList @("api.py") -WorkingDirectory $backend -WindowStyle Hidden
Start-Process -FilePath $node -ArgumentList @("static-server.js") -WorkingDirectory $root -WindowStyle Hidden
Start-Sleep -Seconds 10
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5000/health" -TimeoutSec 20
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:4173/" -TimeoutSec 20
```

Catatan: menjalankan proses server dari sandbox biasa bisa membuat proses mati setelah command selesai. Untuk server yang perlu tetap bisa dibuka browser user, gunakan escalation.

## Cek Port Dan PID

```powershell
netstat -ano | Select-String ":5000|:4173"
```

Port yang diharapkan:

```text
127.0.0.1:5000 LISTENING  # backend FastAPI
127.0.0.1:4173 LISTENING  # frontend static server
```

## Stop Server

Ambil PID dari `netstat`, lalu:

```powershell
Stop-Process -Id <PID>
```

## Test Backend

Compile check:

```powershell
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m py_compile backend\api.py backend\routes\__init__.py backend\routes\auth.py backend\routes\analyses.py backend\routes\health.py backend\modules\analysis_service.py backend\modules\auth_service.py backend\modules\config.py backend\modules\cv_parser.py backend\modules\data_loader.py backend\modules\database.py backend\modules\env_loader.py backend\modules\jobs_service.py backend\modules\nlp.py backend\modules\rate_limit.py
```

Contract tests:

```powershell
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_api_contract.py
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_cv_parser_ocr.py
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_nlp_soft_skills.py
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_recommendation_evaluation.py
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_database_contract.py
```

Work experience test butuh UTF-8 output:

```powershell
$env:PYTHONIOENCODING="utf-8"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" backend\modules\test_work_experience.py
```

## Struktur Backend Setelah Refactor

`backend\api.py` sekarang entrypoint tipis untuk membuat app FastAPI dan include router.

Router:

```text
backend\routes\auth.py
backend\routes\analyses.py
backend\routes\health.py
```

Service utama:

```text
backend\modules\auth_service.py
backend\modules\rate_limit.py
backend\modules\jobs_service.py
backend\modules\analysis_service.py
backend\modules\config.py
backend\modules\cv_parser.py
backend\modules\data_loader.py
backend\modules\database.py
backend\modules\env_loader.py
backend\modules\nlp.py
```

Modul legacy yang tidak dipakai runtime sudah dibersihkan dari backend utama. Jika butuh referensi historis, gunakan arsip di `handoff-zips/` atau folder handoff lain yang memang dipertahankan.
