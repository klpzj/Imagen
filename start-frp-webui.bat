@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_PORT=18000"
set "FRONTEND_PORT=5173"
set "PUBLIC_URL=http://39.106.96.49:15173"

cd /d "%ROOT%"

echo [Imagen] Starting WebUI with FRP...
echo [Imagen] Project: %ROOT%

if not exist "%ROOT%auth.json" (
  echo [ERROR] Missing auth.json. Create it before starting the service.
  pause
  exit /b 1
)

if not exist "%ROOT%frpc.toml" (
  echo [ERROR] Missing frpc.toml. Copy frpc.example.toml to frpc.toml and fill it in.
  pause
  exit /b 1
)

if not exist "%ROOT%frpc.exe" (
  echo [ERROR] Missing frpc.exe. Put frpc.exe in the project root.
  pause
  exit /b 1
)

if not exist "%ROOT%webui\node_modules" (
  echo [Imagen] Installing frontend dependencies...
  pushd "%ROOT%webui"
  call npm install
  if errorlevel 1 (
    popd
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
  popd
)

echo [Imagen] Backend:  http://127.0.0.1:%BACKEND_PORT%
echo [Imagen] Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo [Imagen] Public:   %PUBLIC_URL%
echo [Imagen] Mode:     single window
echo.

set "RUN_DIR=%ROOT%.run"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"

(
  echo @echo off
  echo cd /d "%ROOT%"
  echo python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port %BACKEND_PORT%
) > "%RUN_DIR%\backend.bat"

(
  echo @echo off
  echo cd /d "%ROOT%webui"
  echo npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort
) > "%RUN_DIR%\frontend.bat"

(
  echo @echo off
  echo cd /d "%ROOT%"
  echo frpc.exe -c frpc.toml
) > "%RUN_DIR%\frpc.bat"

start "Imagen Backend" /b cmd /c call "%RUN_DIR%\backend.bat"
timeout /t 2 /nobreak >nul

start "Imagen Frontend" /b cmd /c call "%RUN_DIR%\frontend.bat"
timeout /t 2 /nobreak >nul

start "Imagen FRP" /b cmd /c call "%RUN_DIR%\frpc.bat"

echo [Imagen] Started all processes.
echo [Imagen] Keep this command window open while using the service.
echo [Imagen] Press Ctrl+C to stop the grouped process window.
echo [Imagen] Local:  http://127.0.0.1:%FRONTEND_PORT%
echo [Imagen] Public: %PUBLIC_URL%
echo.

:keepalive
timeout /t 3600 /nobreak >nul
goto keepalive
