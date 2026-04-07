param(
    [Parameter(Position = 0)]
    [ValidateSet("runserver", "migrate", "seed", "check")]
    [string]$Action = "runserver",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtualenv tidak ditemukan di .venv. Buat dulu dengan: python -m venv .venv"
}

$CommandArgs = switch ($Action) {
    "runserver" { @("manage.py", "runserver") + $Args }
    "migrate" { @("manage.py", "migrate") + $Args }
    "seed" { @("seed_fresh_install.py") + $Args }
    "check" { @("manage.py", "check") + $Args }
}

Write-Host "Menggunakan interpreter:" $PythonExe
Write-Host "Menjalankan:" ($CommandArgs -join " ")

& $PythonExe @CommandArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    exit $exitCode
}
