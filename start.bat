@echo off
title NOVEL TL - Launcher
cd /d "%~dp0"

echo ========================================================
echo    NOVEL TL - LOCAL AI EPUB GENERATOR
echo    Running Frontend (Angular) & Backend (FastAPI)...
echo ========================================================
echo.

:: 1. Start Backend in dedicated window
echo [1/2] Menjalankan Backend (FastAPI di http://localhost:8000)...
start "NOVEL TL - [BE] Backend Server (Port 8000)" cmd /k "cd /d "%~dp0" && python server.py"

:: 2. Start Frontend in dedicated window
echo [2/2] Menjalankan Frontend (Angular di http://localhost:4200)...
start "NOVEL TL - [FE] Frontend Angular (Port 4200)" cmd /k "cd /d "%~dp0web" && npm start"

:: 3. Tunggu sebentar lalu buka browser
echo.
echo Menunggu inisialisasi... Membuka browser di http://localhost:4200
timeout /t 4 >nul
start http://localhost:4200

echo.
echo ========================================================
echo   Frontend & Backend sudah berjalan bersamaan:
echo   - Web App UI : http://localhost:4200
echo   - Backend API: http://localhost:8000
echo.
echo   Log server aktif di jendela CMD masing-masing.
echo ========================================================
echo.
pause
