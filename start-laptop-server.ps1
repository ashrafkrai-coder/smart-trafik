$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
$RuntimeDir = Join-Path $ProjectRoot "gateway\runtime"
$BackendLog = Join-Path $RuntimeDir "backend.log"
$BackendErrorLog = Join-Path $RuntimeDir "backend-error.log"
$TunnelOutLog = Join-Path $RuntimeDir "tunnel-out.log"
$TunnelErrorLog = Join-Path $RuntimeDir "tunnel-error.log"

if (-not (Test-Path -LiteralPath $Python)) { throw "Jalankan .\setup-laptop.ps1 dahulu." }
if (-not $Cloudflared) { throw "cloudflared tidak ditemui. Jalankan .\setup-laptop.ps1 dahulu." }
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))) { throw "Fail .env belum tersedia." }

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
Remove-Item -LiteralPath $BackendLog,$BackendErrorLog,$TunnelOutLog,$TunnelErrorLog -Force -ErrorAction SilentlyContinue
$env:ALLOWED_ORIGINS = "https://smart-traffic-dab1e.web.app,https://smart-traffic-dab1e.firebaseapp.com"

$Backend = Start-Process -FilePath $Python -ArgumentList "-m","uvicorn","backend.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrorLog -PassThru
try {
    $Ready = $false
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        if ($Backend.HasExited) { throw "Backend terhenti. Semak gateway\runtime\backend.log" }
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
            $Ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $Ready) { throw "Backend tidak bersedia selepas 60 saat. Semak gateway\runtime\backend.log" }

    $Tunnel = Start-Process -FilePath $Cloudflared -ArgumentList "tunnel","--url","http://127.0.0.1:8000","--no-autoupdate" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $TunnelOutLog -RedirectStandardError $TunnelErrorLog -PassThru
    $PublicUrl = $null
    for ($Attempt = 0; $Attempt -lt 45; $Attempt++) {
        if ($Tunnel.HasExited) { throw "Cloudflare Tunnel terhenti. Semak gateway\runtime\tunnel-error.log" }
        $LogText = ((Get-Content -LiteralPath $TunnelOutLog,$TunnelErrorLog -Raw -ErrorAction SilentlyContinue) -join "`n")
        $Match = [regex]::Match($LogText, "https://[a-z0-9-]+\.trycloudflare\.com")
        if ($Match.Success) { $PublicUrl = $Match.Value; break }
        Start-Sleep -Seconds 1
    }
    if (-not $PublicUrl) { throw "Alamat HTTPS tunnel tidak diterima. Semak log tunnel." }

    $AppUrl = "https://smart-traffic-dab1e.web.app/?server=$([uri]::EscapeDataString($PublicUrl))"
    Write-Host "Laptop server sedang berjalan." -ForegroundColor Green
    Write-Host "Server: $PublicUrl" -ForegroundColor Cyan
    Write-Host "Jangan tutup tetingkap ini. Tekan Ctrl+C untuk berhenti."
    Start-Process $AppUrl
    Wait-Process -Id $Tunnel.Id
} finally {
    if ($Tunnel -and -not $Tunnel.HasExited) { Stop-Process -Id $Tunnel.Id -Force }
    if ($Backend -and -not $Backend.HasExited) { Stop-Process -Id $Backend.Id -Force }
}
