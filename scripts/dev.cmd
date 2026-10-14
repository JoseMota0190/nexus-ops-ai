@echo off
REM ============================================================
REM scripts\dev.cmd — levanta backend + frontend en local (Windows).
REM Se puede doble-clic o correr desde consola. No activa el venv:
REM usa backend\.venv\Scripts\python.exe directo.
REM ============================================================
setlocal
set "RAIZ=%~dp0.."

REM Mock por defecto para no gastar creditos AMD en desarrollo
if "%USE_MOCK%"=="" set "USE_MOCK=true"

REM --- chequeos ---
if not exist "%RAIZ%\backend\.venv\Scripts\python.exe" (
    echo Falta el venv de Python.
    echo Crealo una vez:  cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Backend -^> http://localhost:8000/api/estado
start "Nexus - Backend" /D "%RAIZ%\backend" cmd /k ".venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000"

REM --- frontend (solo si existe) ---
if exist "%RAIZ%\frontend\package.json" (
    echo Frontend -^> http://localhost:5173 (vite)
    start "Nexus - Frontend" /D "%RAIZ%\frontend" cmd /k "npm run dev"
) else (
    echo Todavia no hay frontend ^(falta frontend\package.json^). Se abre solo el backend.
)

endlocal
