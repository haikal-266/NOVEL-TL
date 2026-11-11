@echo off
title Novel TL - EPUB Generator
cd /d "%~dp0"

echo ========================================================
echo   NOVEL TL - EPUB GENERATOR (SUGOI AI)
echo ========================================================
echo.
echo   [1] Jalankan Web App (Browser di http://localhost:8000) [Default]
echo   [2] Jalankan Mode CLI di Terminal
echo.
set /p choice="Pilih mode [1/2] (Tekan Enter = 1): "

if "%choice%"=="2" (
    echo.
    python novel_tl.py
) else (
    echo.
    echo Menjalankan Web Server di http://localhost:8000 ...
    start http://localhost:8000
    python server.py
)
pause

