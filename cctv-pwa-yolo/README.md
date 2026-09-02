# Smart CCTV PWA + YOLOv8

Dashboard PWA jimat data untuk pemantauan CCTV RTSP, dengan analisis kenderaan YOLOv8 dan akses HTTPS melalui Cloudflare Tunnel.

## Aliran sistem

```
[ CCTV RTSP ] ──► [ go2rtc Server ] ──► [ Python + YOLOv8 ] ──► [ traffic_data.json ]
                       │                                                │
                       └──────────────► [ PWA Dashboard ] ◄─────────────┘
                                  (Cloudflare Tunnel / HTTPS)
```

## Prasyarat

- Windows 10/11
- Python 3.10 atau lebih baharu (tanda `Add python.exe to PATH` semasa pemasangan)
- Kamera CCTV dengan RTSP (contoh Hikvision / Dahua / generic ONVIF)
- Sambungan internet (untuk Cloudflare Tunnel dan muat turun model YOLO kali pertama)

## 1. Muat turun executable

Letakkan kedua-dua fail **dalam folder yang sama** dengan `go2rtc.yaml` (`cctv-pwa-yolo/`).

### go2rtc.exe

1. Buka [go2rtc Releases](https://github.com/AlexxIT/go2rtc/releases).
2. Muat turun binaan Windows, contoh: `go2rtc_win64.zip`.
3. Ekstrak dan namakan semula / salin `go2rtc.exe` ke folder projek.

### cloudflared.exe

1. Buka [cloudflared Releases](https://github.com/cloudflare/cloudflared/releases).
2. Muat turun `cloudflared-windows-amd64.exe`.
3. Namakan semula kepada `cloudflared.exe` dan letakkan dalam folder projek.

Akaun Cloudflare **tidak wajib** untuk quick tunnel (`cloudflared tunnel --url ...`). URL `https://*.trycloudflare.com` akan dipaparkan dalam terminal cloudflared.

## 2. Tetapkan kamera RTSP

Edit `go2rtc.yaml`. Ganti URL contoh dengan stream sebenar:

```yaml
streams:
  pintu_depan:
    - rtsp://USER:PASSWORD@192.168.1.101:554/Streaming/Channels/101
  halaman:
    - rtsp://USER:PASSWORD@192.168.1.102:554/Streaming/Channels/101
  dapur:
    - rtsp://USER:PASSWORD@192.168.1.103:554/Streaming/Channels/101
```

Petua:

- Saluran utama biasanya `101` / `stream1`; saluran sub (lebih ringan) `102` / `stream2`.
- Jika kata laluan mengandungi aksara khas (`@`, `#`, `/`), URL-encode aksara tersebut.
- CORS sudah ditetapkan `origin: "*"` supaya `/api/frame.jpeg` boleh dipanggil dari pelayar.

## 3. Pasang pustaka Python

Dalam PowerShell atau Command Prompt, dari folder `cctv-pwa-yolo`:

```bat
python -m pip install --upgrade pip
python -m pip install ultralytics opencv-python numpy
```

Atau:

```bat
python -m pip install -r requirements.txt
```

Model `yolov8n.pt` dimuat turun secara automatik pada larian pertama (saiz kecil, sesuai CPU).

## 4. Pelancaran

Klik dua kali `start_cctv_backend.bat`. Tiga tetingkap akan dibuka:

| Tetingkap | Fungsi |
|-----------|--------|
| go2rtc | Media server RTSP → snapshot JPEG + WebRTC |
| cloudflared | Terowong HTTPS ke `http://localhost:1984` |
| YOLOv8 | Poll snapshot `pintu_depan` setiap 3 saat, tulis `traffic_data.json` |

Dashboard tempatan:

- [http://localhost:1984/index.html](http://localhost:1984/index.html)

go2rtc `static_dir: "."` menghidangkan PWA dan `traffic_data.json` dari origin yang sama, jadi tiada pelayan web tambahan diperlukan. Fail `stream.html` disertakan kerana folder statik ini menggantikan UI terbina dalam go2rtc; modal **Live Stream** menggunakan WebRTC (`/api/webrtc`) dengan fallback MSE (`/api/stream.mp4`).

## 5. Checklist operasi

- [ ] `go2rtc.exe` dan `cloudflared.exe` ada dalam folder projek
- [ ] URL RTSP dalam `go2rtc.yaml` telah dikemaskini
- [ ] `python -m pip install ultralytics opencv-python numpy` berjaya
- [ ] `start_cctv_backend.bat` dilancarkan
- [ ] Terminal go2rtc menunjukkan stream tanpa ralat auth
- [ ] [http://localhost:1984/api/frame.jpeg?src=pintu_depan](http://localhost:1984/api/frame.jpeg?src=pintu_depan) memaparkan JPEG
- [ ] Terminal YOLO mencetak badge seperti `🚗 5 Kenderaan | Kepadatan: Sederhana`
- [ ] Dashboard: lencana **ONLINE** hijau, overlay trafik, cap masa `HH:MM:SS`
- [ ] Butang **Live Stream** membuka modal WebRTC (`/stream.html?src=...&mode=webrtc`)
- [ ] URL `trycloudflare.com` dari terminal cloudflared dibuka di telefon (HTTPS)
- [ ] Pada mudah alih: **Add to Home Screen** (PWA)

## Jimat data

Dashboard **tidak** memainkan video berterusan. Ia memuat JPEG statik setiap 3 saat (`/api/frame.jpeg?src=<id>&t=<timestamp>`). WebRTC hanya diaktifkan apabila pengguna menekan **Live Stream**.

## Kepadatan trafik

| Jumlah kenderaan | Tahap |
|------------------|--------|
| &lt; 3 | Rendah |
| 3–7 | Sederhana |
| &gt; 7 | Tinggi |

Kelas COCO yang dikira: kereta (2), motosikal (3), bas (5), lori (7). Kamera analisis lalai ialah `pintu_depan`.

## Pembolehubah persekitaran (pilihan)

```bat
set GO2RTC_SNAPSHOT_URL=http://localhost:1984/api/frame.jpeg?src=halaman
set TRAFFIC_CAMERA_ID=halaman
set TRAFFIC_POLL_INTERVAL=3
set YOLO_CONF=0.35
python traffic_analyzer.py
```

## Penyelesaian masalah

| Gejala | Tindakan |
|--------|----------|
| Snapshot gagal / OFFLINE | Semak IP, port 554, user/password, dan firewall kamera |
| CORS di DevTools | Pastikan `api.origin: "*"` dalam `go2rtc.yaml` dan muat semula go2rtc |
| YOLO ralat snapshot | Tunggu go2rtc sedia (~3 saat); pastikan `src=pintu_depan` wujud |
| CPU tinggi | Kekalkan `yolov8n.pt`; jangan tukar ke `yolov8s/m` tanpa GPU |
| WebRTC hitam | Cuba Chrome/Edge; benarkan autoplay; semak UDP WebRTC pada rangkaian |
| PWA tidak install | Mesti dibuka melalui HTTPS (tunnel) atau localhost, bukan `file://` |
