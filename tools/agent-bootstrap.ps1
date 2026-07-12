param(
    [switch]$Dev,
    [switch]$IPhone
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "RPA-Everything Agent bootstrap (Windows)"

$SetupArgs = @()
if ($Dev) { $SetupArgs += "-Dev" }
if ($IPhone) { $SetupArgs += "-IPhone" }
& "$PSScriptRoot\setup.ps1" @SetupArgs

$Python = Join-Path $Root ".venv\Scripts\python.exe"
Write-Host "`n[check] Running safe doctor setup"
& $Python run.py harness/doctor --fix --required-only
$DoctorExit = $LASTEXITCODE

Write-Host "`n[demo] Running the no-key lifecycle preview"
& $Python run.py harness/demo

Write-Host "`nBootstrap complete."
if ($DoctorExit -ne 0) {
    Write-Host "LLM configuration is still expected to be incomplete. Add llm.api_key / llm.model to config.yaml before planning a real task."
}
Write-Host "Next safe command: $Python run.py harness/agent -- --goal `"Plan a read-only task only. Do not submit, publish, send, approve, pay, delete, or modify remote data.`" --dry-run"
