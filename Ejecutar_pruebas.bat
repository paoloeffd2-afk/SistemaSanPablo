@echo off
rem Doble clic: ejecuta las pruebas automatizadas (pytest) y deja la ventana abierta para ver el resultado.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PYCMD=py) else (set PYCMD=python)
%PYCMD% -c "import pytest, cryptography" >nul 2>nul
if errorlevel 1 (
  echo Instalando pytest y cryptography, un momento...
  %PYCMD% -m pip install pytest cryptography
)
%PYCMD% -m pytest -v
echo.
pause
