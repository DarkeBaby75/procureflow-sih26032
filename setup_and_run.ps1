$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectDir

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env. Add Gmail App Password details there to enable email delivery." -ForegroundColor Yellow
}

Write-Host "ProcureFlow is starting at http://127.0.0.1:5000" -ForegroundColor Green
& ".\.venv\Scripts\python.exe" "serve.py"

