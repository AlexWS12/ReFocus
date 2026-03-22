# to run tests, do: cd src/vision/tests && ./test.ps1

$ErrorActionPreference = 'Stop'

# Resolve project root from this script location.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
Set-Location $projectRoot

# Prefer workspace virtualenv on Windows.
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe -m pytest src/vision/tests -q @args
} else {
    python -m pytest src/vision/tests -q @args
}
