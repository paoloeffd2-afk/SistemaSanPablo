@echo off
rem Doble clic: instala lo que falte (una sola vez) y abre la aplicacion en ventana.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PYCMD=py) else (set PYCMD=python)
%PYCMD% -c "import cryptography" >nul 2>nul
if errorlevel 1 (
  echo Instalando componente de cifrado, un momento...
  %PYCMD% -m pip install -r requirements.txt
)
start "" %PYCMD%w main.py
