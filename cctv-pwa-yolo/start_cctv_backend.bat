@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title CCTV PWA YOLO — Pelancar Backend
color 0A

echo ============================================================
echo   CCTV PWA + YOLOv8 — Pelancaran Backend
echo   Folder: %CD%
echo ============================================================
echo.

if not exist "go2rtc.exe" (
  echo [RALAT] go2rtc.exe tidak dijumpai dalam folder ini.
  echo Muat turun dari: https://github.com/AlexxIT/go2rtc/releases
  goto :fail
)

if not exist "cloudflared.exe" (
  echo [RALAT] cloudflared.exe tidak dijumpai dalam folder ini.
  echo Muat turun dari: https://github.com/cloudflare/cloudflared/releases
  goto :fail
)

if not exist "go2rtc.yaml" (
  echo [RALAT] go2rtc.yaml tidak dijumpai.
  goto :fail
)

where python >nul 2>&1
if errorlevel 1 (
  echo [RALAT] Python tidak dijumpai dalam PATH.
  echo Pasang Python 3.10+ dan semak "Add python.exe to PATH".
  goto :fail
)

echo [1/3] Memulakan go2rtc (port 1984)...
start "go2rtc — CCTV Media Server" /D "%CD%" cmd /k "go2rtc.exe"

timeout /t 3 /nobreak >nul

echo [2/3] Memulakan Cloudflare Tunnel (HTTPS)...
start "cloudflared — Cloudflare Tunnel" /D "%CD%" cmd /k "cloudflared.exe tunnel --url http://localhost:1984"

timeout /t 2 /nobreak >nul

echo [3/3] Memulakan analisis trafik YOLOv8...
start "YOLOv8 — Traffic Analyzer" /D "%CD%" cmd /k "python traffic_analyzer.py"

echo.
echo ------------------------------------------------------------
echo   Tiga tetingkap terminal telah dibuka:
echo     1. go2rtc          — http://localhost:1984
echo     2. cloudflared     — salin URL https://*.trycloudflare.com
echo     3. traffic_analyzer — menulis traffic_data.json
echo.
echo   Dashboard PWA (rangkaian tempatan):
echo     http://localhost:1984/index.html
echo ------------------------------------------------------------
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1
