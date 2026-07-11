param(
    [switch]$Dev,
    [switch]$IPhone
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "RPA-Everything setup (Windows)"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/5] Creating .venv"
    py -3.12 -m venv .venv
} else {
    Write-Host "[1/5] .venv already exists"
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "[2/5] Upgrading pip"
& $Python -m pip install --upgrade pip

Write-Host "[3/5] Installing Python dependencies"
if ($Dev) {
    & $Python -m pip install -r requirements-dev.txt
} else {
    & $Python -m pip install -r requirements.txt
}

if ($IPhone) {
    Write-Host "[3b/5] Installing optional iPhone dependency"
    & $Python -m pip install pymobiledevice3
}

Write-Host "[4/5] Installing Playwright Chromium"
& $Python -m playwright install chromium

if (-not (Test-Path "config.yaml")) {
    Write-Host "[5/5] Creating config.yaml from template"
    Copy-Item "config.yaml.example" "config.yaml"
} else {
    Write-Host "[5/5] config.yaml already exists"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "  1. Open config.yaml and fill llm.api_key / llm.model."
Write-Host "  2. Run: .\.venv\Scripts\python.exe run.py harness/doctor"
Write-Host "  3. Start browser tasks with: tools\start_chrome.bat"
