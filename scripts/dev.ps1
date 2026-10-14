# ============================================================
# scripts/dev.ps1 — levanta backend + frontend en local (Windows).
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
# (o doble clic en scripts\dev.cmd, que hace lo mismo)
#
# No activa el venv: usa backend\.venv\Scripts\python.exe directo.
# ============================================================
$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz "backend\.venv\Scripts\python.exe"
$frontendDir = Join-Path $raiz "frontend"

# --- chequeos ---
if (-not (Test-Path $python)) {
    Write-Host "Falta el venv de Python." -ForegroundColor Red
    Write-Host "Crealo una vez:  cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "Todavia no hay frontend (falta frontend/package.json). Se abre solo el backend." -ForegroundColor Yellow
    $soloBackend = $true
}
if (-not (Test-Path (Join-Path $raiz ".env"))) {
    Write-Host "Aviso: no existe .env — se usa modo mock por defecto (copiá .env.example a .env para customizar)." -ForegroundColor Yellow
}

# Mock por defecto para no gastar créditos AMD en desarrollo
if (-not $env:USE_MOCK) { $env:USE_MOCK = "true" }

Write-Host "Backend  -> http://localhost:8000/api/estado" -ForegroundColor Cyan
if (-not $soloBackend) { Write-Host "Frontend -> http://localhost:5173 (vite)" -ForegroundColor Cyan }
Write-Host "Para cortar: cerrar las ventanas o Ctrl+C en cada una." -ForegroundColor DarkGray

# --- backend (ventana propia, con --reload) ---
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$raiz\backend'; & '$python' -m uvicorn api:app --reload --port 8000"
)

# --- frontend (ventana propia, vite dev server) ---
if (-not $soloBackend) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$frontendDir'; npm run dev"
    )
}
