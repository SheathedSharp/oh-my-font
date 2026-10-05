@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 build-local.py %*
) else (
  python build-local.py %*
)
if errorlevel 1 (
  echo.
  echo Build failed. Install Python 3.10 or newer and check the error above.
  pause
  exit /b 1
)
echo.
echo Built into dist. No fonts have been installed automatically.
pause
