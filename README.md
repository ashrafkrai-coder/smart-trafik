# Smart Trafik

Smart Trafik ialah dashboard PWA vanilla JavaScript dengan backend FastAPI. OpenCV membaca MP4, Ultralytics YOLO mengesan kereta, motosikal, bas dan lori, dan keadaan live disimpan dalam memori. Ringkasan berkala sahaja dihantar ke Cloud Firestore.

```text
Video MP4 / CCTV
       ↓
OpenCV + YOLO → shared state FastAPI → dashboard
                         ↓ setiap 60 saat
                    Cloud Firestore
```

Video dan frame tidak pernah disimpan dalam Firestore. Frontend tidak mempunyai SDK Admin, service account, private key, atau akses terus ke Firestore.

## Struktur projek

```text
frontend/             Dashboard, manifest, service worker, offline page dan ikon
backend/              FastAPI, YOLO, video worker dan konfigurasi
backend/repositories/ Akses Firestore yang diasingkan
backend/services/     Worker ringkasan, heartbeat dan amaran
videos/               Sumber video tempatan
credentials/          Dokumentasi sahaja; semua credentials diabaikan Git
tests/                 Ujian unit menggunakan mock, bukan Firebase sebenar
```

## 1. Cipta virtual environment

Gunakan Python 3.10 atau lebih baharu dalam PowerShell di root projek:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

CUDA tidak diwajibkan; model nano boleh berjalan pada CPU, tetapi lebih perlahan.

## 2. Sediakan Firebase

1. Buka Firebase Console dan cipta atau pilih projek.
2. Buka **Firestore Database** dan klik **Create database**.
3. Pilih lokasi yang sesuai untuk pengguna sistem.
4. Pergi ke **Project settings → Service accounts**.
5. Klik **Generate new private key**.
6. Simpan JSON itu di lokasi selamat, sebaiknya di luar repository.
7. Jangan commit ke GitHub dan jangan masukkan kandungannya ke frontend atau chat.

Admin SDK menggunakan IAM/Application Default Credentials. `firestore.rules` sengaja deny-by-default kerana browser tidak mengakses Firestore.

## 3. Tetapkan credentials

Tetapkan pemboleh ubah dalam terminal yang sama sebelum menjalankan backend:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\lokasi\selamat\service-account.json"
```

Salin `.env.example` kepada `.env` dan isi project ID tanpa meletakkan rahsia:

```powershell
Copy-Item .env.example .env
```

Jika mahu menjalankan demo tanpa Firestore:

```powershell
$env:FIREBASE_ENABLED="false"
```

Tanpa credentials, analisis live dan MJPEG terus berfungsi; `/health` melaporkan `firebase_connected: false`, manakala endpoint sejarah/amaran memberi ralat 503 terkawal.

## 4. Letakkan video

```text
videos/trafik.mp4
```

MP4 diulang apabila tamat. Ia tidak dimuat naik ke Firestore atau Git. Sumber RTSP yang mengandungi username/kata laluan mesti berada dalam environment backend sahaja.

## 5. Jalankan backend

```powershell
.\run.ps1
```

Model utama ialah `yolo26n.pt`; backend mencuba model nano rasmi fallback `yolo11n.pt` jika model utama tidak dapat dimuatkan. Muat turun model pertama kali mungkin memerlukan internet.

## 6. Uji API

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/traffic`
- `http://127.0.0.1:8000/api/traffic/history?camera_id=CAM01&limit=50`
- `http://127.0.0.1:8000/api/cameras`
- `http://127.0.0.1:8000/api/alerts`
- `http://127.0.0.1:8000/video-feed`
- `http://127.0.0.1:8000/docs`

`/api/traffic` membaca shared state sahaja dan tidak membuat query Firestore. Frontend mengambil live state setiap dua saat, manakala backend menulis satu batch `traffic_latest` + `traffic_records` mengikut `TRAFFIC_SAVE_INTERVAL_SECONDS` (default 60 saat). Heartbeat mempunyai sela tersendiri dan amaran dideduplicate dengan transition, semakan amaran aktif dan cooldown.

## 7. Jalankan frontend

Dalam VS Code, klik kanan `frontend/index.html` dan pilih **Open with Live Server**. Gunakan origin `http://127.0.0.1:5500` atau `http://localhost:5500`; jangan guna `file://` kerana service worker memerlukan HTTP/HTTPS.

Dashboard menghentikan polling ketika tab tidak aktif, membatalkan request tertunggak, dan menyambung semula apabila tab aktif. Data live dibersihkan apabila API offline supaya data lama tidak kelihatan sebagai data semasa.

## Firestore dan deploy konfigurasi

Collection yang digunakan ialah `cameras`, `traffic_latest`, `traffic_records`, `traffic_alerts`, dan `system_status/backend`. Timestamp penulisan menggunakan server timestamp. Query mempunyai had dan sejarah disusun terbaru dahulu.

Selepas memasang Firebase CLI dan memilih projek yang betul, rules dan index boleh dideploy secara manual:

```powershell
firebase deploy --only firestore:rules,firestore:indexes
```

Semak projek aktif sebelum deploy. Backend Admin SDK menggunakan IAM, bukan rules klien.

## Anggaran demonstrasi

**Anggaran kelajuan aliran** dan **anggaran masa perjalanan** ialah nilai demonstrasi berdasarkan kategori Lancar/Sesak/Sangat Sesak. Ia bukan kelajuan sebenar. Ukuran tepat memerlukan kalibrasi kamera, jarak dunia sebenar, perspective transform, tracking objek dan FPS stabil.

Klasifikasi menggunakan purata bergerak sekurang-kurangnya 10 frame: 0–10 Lancar, 11–25 Sesak dan 26+ Sangat Sesak.

## Ujian selamat

Ujian Firebase menggunakan objek mock dan tidak menulis ke projek sebenar:

```powershell
python -m compileall backend
pytest
python -c "from backend.main import app; print(app.title)"
```

## Penyelesaian masalah

- **`python is not recognized`** — pasang Python 3.10+ dan tandakan *Add Python to PATH*, kemudian buka semula VS Code.
- **`Activate.ps1 cannot be loaded`** — jalankan `Set-ExecutionPolicy -Scope Process Bypass`, kemudian aktifkan `.venv` semula.
- **Credentials tidak dijumpai / `DefaultCredentialsError`** — semak path fail dan tetapkan `GOOGLE_APPLICATION_CREDENTIALS` dalam terminal backend yang sama. Jangan letak private key dalam `.env`.
- **Firestore database belum dicipta** — buka Firebase Console → Firestore Database → Create database.
- **Firestore permission error** — semak IAM service account dan project ID. Rules klien deny-by-default tidak menyekat Admin SDK yang sah.
- **Indeks diperlukan** — deploy `firestore.indexes.json` atau gunakan link penciptaan indeks dalam log Firestore selepas memastikan query sepadan.
- **Firebase offline** — live YOLO terus berjalan. Semak `/health`; retry berlaku mengikut sela, bukan setiap frame.
- **Video tidak dijumpai** — pastikan `videos/trafik.mp4` wujud dan boleh dibaca OpenCV.
- **Model gagal dimuat turun** — semak internet/firewall atau letakkan model nano `.pt` dalam folder `models`.
- **YOLO terlalu perlahan** — kurangkan `IMAGE_SIZE`/`PROCESSING_FPS`, gunakan video 720p, atau gunakan GPU yang serasi.
- **Port 8000 digunakan** — hentikan server lama dengan `Ctrl+C` atau kenal pasti proses yang menggunakan port itu.
- **CORS error** — jalankan Live Server pada port 5500 atau tambah origin tepat dalam `ALLOWED_ORIGINS`.
- **Dashboard menunjukkan Offline** — semak backend, `/health`, fail video dan status model; tekan *Cuba semula* selepas punca dibetulkan.

## Keselamatan

`.gitignore` mengecualikan `.env`, `credentials/`, corak service-account/Firebase Admin SDK, model dan video. Log hanya merekod jenis kegagalan Firebase dan tidak mencetak credentials, token atau private key. Jangan ubah rules kepada `allow read, write: if true`.
