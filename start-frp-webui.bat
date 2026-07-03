@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_PORT=18000"
set "FRONTEND_PORT=5173"
set "PUBLIC_URL=http://39.106.96.49:15173"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\start-frp-webui.ps1" -BackendPort %BACKEND_PORT% -FrontendPort %FRONTEND_PORT% -PublicUrl "%PUBLIC_URL%"
if errorlevel 1 (
  echo.
  echo [Imagen] Startup failed. See the error above and logs in .run.
  pause
  exit /b 1
)

endlocal
