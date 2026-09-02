$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Membuat virtual environment di .venv..."
    & python -m venv $venvPath
}

Write-Host "Mengemas kini pip..."
& $pythonPath -m pip install --upgrade pip

$torchCuda = & $pythonPath -c "import torch; print(torch.version.cuda or '')" 2>$null
if (($torchCuda -join "").Trim() -ne "12.4") {
    $requiredFreeBytes = 5GB
    $driveName = (Split-Path -Qualifier $projectRoot).TrimEnd(':')
    $freeBytes = (Get-PSDrive -Name $driveName).Free
    if ($freeBytes -lt $requiredFreeBytes) {
        $freeGb = [math]::Round($freeBytes / 1GB, 2)
        throw "Ruang kosong $driveName`: hanya $freeGb GB. Sediakan sekurang-kurangnya 5 GB sebelum memasang PyTorch CUDA."
    }
    Write-Host "Memasang PyTorch dengan CUDA 12.4..."
    & $pythonPath -m pip install --upgrade --force-reinstall --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch torchvision
} else {
    Write-Host "PyTorch CUDA 12.4 sudah terpasang; tidak mengunduh ulang."
}

Write-Host "Memasang dependency backend..."
& $pythonPath -m pip install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "Memeriksa CUDA..."
$cudaCheck = & $pythonPath -c "import torch; print('torch=' + torch.__version__); print('cuda_build=' + str(torch.version.cuda)); print('cuda_available=' + str(torch.cuda.is_available())); print('gpu=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'))"
$cudaCheck | Write-Host
if (-not (($cudaCheck -join "`n") -match "cuda_available=True")) {
    throw "PyTorch terpasang tetapi CUDA tidak tersedia. Semak driver NVIDIA dan TORCH_DEVICE."
}

Write-Host "Setup CUDA selesai. Jalankan backend dengan: .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload"
