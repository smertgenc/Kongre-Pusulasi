@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Build bilgisayarinda Python 3.12 x64 gereklidir. Son kullaniciya Python kurulmaz.
  exit /b 1
)
if not exist ".venv-build\Scripts\python.exe" (
  py -3.12 -m venv .venv-build
  if errorlevel 1 exit /b 1
)
".venv-build\Scripts\python.exe" -m pip install -r packaging\windows\requirements-build.txt
if errorlevel 1 exit /b 1
".venv-build\Scripts\python.exe" tools\build_windows.py %*
exit /b %errorlevel%
