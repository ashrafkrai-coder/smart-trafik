$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command python -ErrorAction SilentlyContinue

if (-not $Python) {
    throw "Python tidak ditemui. Pasang Python 3.10 atau lebih baharu dan tandakan Add Python to PATH."
}

Set-Location -LiteralPath $ProjectRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "cloudflared belum dipasang dan winget tidak ditemui. Pasang Cloudflare Tunnel kemudian jalankan skrip ini semula."
    }
    winget install --id Cloudflare.cloudflared --exact --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.laptop.example" -Destination ".env"
    Write-Host "Fail .env telah dicipta. Isi alamat RTSP, username dan password CCTV dahulu." -ForegroundColor Yellow
}

Write-Host "Persediaan laptop selesai." -ForegroundColor Green
Write-Host "Selepas mengisi .env, jalankan: .\start-laptop-server.ps1"
