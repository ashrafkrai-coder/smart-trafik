# Jalankan backend Smart Trafik dalam virtual environment projek.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"

# Terminal VS Code yang sudah terbuka mungkin belum mewarisi environment
# peringkat pengguna. Ambil nilainya tanpa memaparkan path atau isi credentials.
if (-not $env:GOOGLE_APPLICATION_CREDENTIALS) {
    $UserFirebaseCredentials = [Environment]::GetEnvironmentVariable(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "User"
    )
    if ($UserFirebaseCredentials) {
        $env:GOOGLE_APPLICATION_CREDENTIALS = $UserFirebaseCredentials
    }
}

if (-not (Test-Path -LiteralPath $VenvActivate)) {
    Write-Host "Virtual environment .venv belum tersedia." -ForegroundColor Yellow
    Write-Host "Jalankan: python -m venv .venv"
    Write-Host "Kemudian: .venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}

$FirebaseDisabled = $env:FIREBASE_ENABLED -and $env:FIREBASE_ENABLED.ToLowerInvariant() -eq "false"
if (-not $FirebaseDisabled -and -not $env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Warning "GOOGLE_APPLICATION_CREDENTIALS belum ditetapkan. Backend akan berjalan, tetapi Firebase mungkin offline kecuali Application Default Credentials lain tersedia."
}
if ($FirebaseDisabled) {
    Write-Host "Firebase dinyahaktifkan melalui FIREBASE_ENABLED=false." -ForegroundColor Yellow
}

Set-Location -LiteralPath $ProjectRoot
& $VenvActivate
Write-Host "Smart Trafik API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Tekan Ctrl+C untuk berhenti."
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
