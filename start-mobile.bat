@echo off
title NOVEL TL - Mobile App Launcher
cd /d "%~dp0"

echo ========================================================
echo    NOVEL TL - MOBILE APP (EXPO REACT NATIVE)
echo    Starting Backend (FastAPI) & Mobile Bundler (Expo)...
echo ========================================================
echo.

:: 1. Start Backend Server
echo [1/2] Menjalankan Backend (FastAPI di port 8000)...
start "NOVEL TL - [BE] Backend Server (Port 8000)" cmd /k "cd /d "%~dp0" && python server.py"

:: 2. Start Expo Mobile Server
echo [2/2] Menjalankan Expo React Native Mobile App...
start "NOVEL TL - [MOBILE] Expo Bundler" cmd /k "cd /d "%~dp0mobile" && npx expo start"

echo.
echo ========================================================
echo   Server & Mobile Bundler sudah aktif!
echo.
echo   Cara Buka di HP (Android / iOS):
echo   1. Buka aplikasi "Expo Go" di HP (Download di Google Play Store).
echo   2. Scan QR Code yang muncul di jendela CMD [MOBILE].
echo   3. Pastikan HP dan PC terhubung ke Wi-Fi yang sama.
echo ========================================================
echo.
pause

