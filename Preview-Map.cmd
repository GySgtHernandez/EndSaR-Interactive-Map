@echo off
rem Double-click to open the map from this folder in your browser (http://localhost:8765/).
rem Close this window to stop the preview.
cd /d "%~dp0site"
set PORT=8765
title EndSaR map preview (close this window to stop)
python -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  echo Map preview running at http://localhost:%PORT%/  - close this window to stop.
  start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:%PORT%/"
  python -m http.server %PORT% --bind 127.0.0.1
  goto :end
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\serve.ps1" -Port %PORT% -Root "%~dp0site"
:end
echo.
echo The preview has stopped. If you saw an error, close any other preview window and try again.
pause
