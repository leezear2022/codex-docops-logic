@echo off
setlocal
set "DOL_SCRIPT=%~dp0dol.py"

if defined DOCOPS_PYTHON (
  "%DOCOPS_PYTHON%" "%DOL_SCRIPT%" %*
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if %errorlevel% equ 0 (
    py -3 "%DOL_SCRIPT%" %*
    exit /b %errorlevel%
  )
)

where python >nul 2>nul
if %errorlevel% equ 0 (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if %errorlevel% equ 0 (
    python "%DOL_SCRIPT%" %*
    exit /b %errorlevel%
  )
)

>&2 echo DocOps Logic requires Python 3.11 or newer. Install Python, enable py/python, or set DOCOPS_PYTHON to python.exe.
exit /b 9009
