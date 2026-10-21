# Start the CodeLens API (port 8000) and the Vite client (port 5173).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    python -m venv venv
}

& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Set GROQ_API_KEY in that file before model calls will succeed."
}

$Kb = Join-Path $Root "codelens_kb"
if (-not (Test-Path $Kb)) {
    Write-Host "Building the debugging knowledge base (first run downloads the embedding model)..."
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & ".\venv\Scripts\python.exe" -m rag_core.build_kb
    $KbExit = $LASTEXITCODE
    $ErrorActionPreference = $PreviousPreference
    if ($KbExit -ne 0) {
        Write-Host "Knowledge base build failed. POST /ask can still run, but debugging answers will have no retrieved notes."
    }
}

$Backend = Start-Process `
    -FilePath ".\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "rag_core.api:app", "--reload", "--port", "8000" `
    -WorkingDirectory $Root `
    -PassThru `
    -WindowStyle Hidden

Write-Host "API:    http://localhost:8000"
Write-Host "Client: http://localhost:5173"

try {
    Set-Location (Join-Path $Root "frontend")
    if (-not (Test-Path ".\node_modules")) {
        npm install
    }
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
    }
    npm run dev
}
finally {
    $ErrorActionPreference = "Continue"
    if ($Backend -and -not $Backend.HasExited) {
        & taskkill.exe /PID $Backend.Id /T /F | Out-Null
    }
}
