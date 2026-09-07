$ErrorActionPreference = "Stop"
$DolScript = Join-Path $PSScriptRoot "dol.py"

if ($env:DOCOPS_PYTHON) {
    & $env:DOCOPS_PYTHON $DolScript @args
    exit $LASTEXITCODE
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
    & $PyLauncher.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $PyLauncher.Source -3 $DolScript @args
        exit $LASTEXITCODE
    }
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    & $Python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $Python.Source $DolScript @args
        exit $LASTEXITCODE
    }
}

Write-Error "DocOps Logic requires Python 3.11 or newer. Install Python, enable py/python, or set DOCOPS_PYTHON to python.exe."
exit 9009
