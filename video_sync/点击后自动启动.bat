@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE="
if exist "%~dp0..\.venv\Scripts\python.exe" (
  set "PY_EXE=%~dp0..\.venv\Scripts\python.exe"
)
if not defined PY_EXE (
  if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
  )
)
if not defined PY_EXE (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python and make sure "python" command works.
    pause
    exit /b 1
  )
  set "PY_EXE=python"
)

echo Using Python: %PY_EXE%
"%PY_EXE%" "%~dp0scripts\launch_web.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Web app failed to start.
  echo Try:
  echo   "%PY_EXE%" -m pip install -r "%~dp0requirements.txt"
  pause
  exit /b 1
)

endlocal
