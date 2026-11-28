@echo off
rem Thin launcher: finds a Python 3.8+ and runs orchestrate.py next to this file.
set "D=%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%D%orchestrate.py" %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "%D%orchestrate.py" %*
  exit /b %errorlevel%
)
echo orchestrate: Python 3.8+ was not found. Install it from https://www.python.org/downloads/ 1>&2
exit /b 127
