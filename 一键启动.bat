@echo off
chcp 65001 >nul
title pose3d 双机位视频分析系统

echo ============================================
echo   pose3d - 双机位视频分析系统
echo ============================================
echo.

:: Step 1: Build frontend
echo [1/2] Building frontend...
cd /d "%~dp0frontend"
call npm.cmd run build
if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] Frontend build failed!
    pause
    exit /b 1
)
echo [OK] Frontend built successfully.
echo.

:: Step 2: Start Flask
echo [2/2] Starting Flask server...
echo.
cd /d "%~dp0web_1"
python v1.py
pause
