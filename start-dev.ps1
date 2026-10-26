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
    Write-Host "Created .env. Set GROQ_API_KEY and JWT_SECRET in that file before model calls and shared logins will succeed."
}

function Add-EnvDefault($Name, $Value) {
    if (-not (Select-String -Path ".env" -Pattern "^$Name=" -Quiet)) {
        Add-Content -Path ".env" -Value "$Name=$Value"
        Write-Host "Added $Name to .env"
    }
}

Add-EnvDefault "MONGODB_URI" "mongodb://localhost:27017"
Add-EnvDefault "MONGODB_DB" "codelens"
Add-EnvDefault "JWT_SECRET" "change-me-to-a-long-random-string"

function Test-MongoPort {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $wait = $client.BeginConnect("127.0.0.1", 27017, $null, $null)
        $opened = $wait.AsyncWaitHandle.WaitOne(500, $false)
        if (-not $opened) { return $false }
        $client.EndConnect($wait)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-MongoPort)) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "MongoDB is not on port 27017. Starting it with docker compose..."
        docker compose up -d
        foreach ($i in 1..20) {
            Start-Sleep -Seconds 1
            if (Test-MongoPort) { break }
        }
    }
    if (-not (Test-MongoPort)) {
        Write-Host "MongoDB is not listening on localhost:27017."
        Write-Host "Install MongoDB Community Server (it listens on 27017 by default), or install Docker and run: docker compose up -d"
        Write-Host "winget install MongoDB.Server"
    }
} else {
    Write-Host "MongoDB is listening on localhost:27017"
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
