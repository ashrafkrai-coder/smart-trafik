# HTTPS/HLS CCTV Gateway

Gateway ini perlu dijalankan pada PC/Raspberry Pi yang berada dalam LAN sama
dengan CCTV. Firebase Hosting atau Cloud Run tidak boleh mencapai alamat private
`192.168.1.64` secara terus.

## Setup

1. Pasang Docker Desktop pada mesin gateway. Docker belum dipasang pada mesin
   development ini.
2. Salin `.env.gateway.example` kepada `.env.gateway`.
3. Isi `CCTV_RTSP_URL` dengan URL RTSP sebenar. Jika password mempunyai aksara
   khas, URL-encode dahulu. Jangan commit fail `.env.gateway`.
4. Tukar `HLS_DOMAIN` kepada hostname awam yang DNS-nya menunjuk ke gateway.
5. Pastikan port TCP `80` dan `443` sampai ke gateway, kemudian jalankan:

   ```powershell
   docker compose --env-file .env.gateway up -d
   ```

MediaMTX membaca RTSP dan menyediakan playlist HLS pada `/cctv/index.m3u8`.
Caddy meneruskan endpoint itu melalui HTTPS dan mendapatkan sijil TLS secara
automatik untuk hostname awam. Uji dari gateway dahulu:

```text
http://127.0.0.1:8888/cctv/index.m3u8
```

Selepas DNS/TLS siap, URL PWA ialah:

```text
https://HLS_DOMAIN/cctv/index.m3u8
```

Jika tidak mahu buka port router, gunakan Cloudflare Tunnel dari mesin gateway
dan hala hostname tunnel kepada `http://localhost:8888`. Dalam kes itu, URL
public tunnel tetap digunakan sebagai `CCTV_HLS_URL`.

## Build PWA

Di GitHub, tambah repository secret `CCTV_HLS_URL` dengan URL HTTPS HLS di atas.
Workflow akan membina PWA menggunakan secret itu. Untuk ujian local:

```powershell
cd frontend
$env:VITE_HLS_URL = "https://cctv.example.com/cctv/index.m3u8"
npm run build
```

Jika `VITE_HLS_URL` kosong, PWA kembali menggunakan endpoint MJPEG backend local.
Hanya URL HLS public masuk ke frontend; credential RTSP tidak pernah dihantar
ke browser.
