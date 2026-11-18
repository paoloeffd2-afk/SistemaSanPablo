@echo off
rem Doble clic: muestra que Python usa tu PC y por que no abre. La ventana NO se cierra sola.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PYCMD=py) else (set PYCMD=python)
echo ===== 1. Python =====
echo Comando usado: %PYCMD%
%PYCMD% --version
%PYCMD% -c "import sys; print(sys.executable)"
echo.
echo ===== 2. Instalar lo necesario (se ve todo el resultado) =====
%PYCMD% -m pip install cryptography pytest
echo.
echo ===== 3. Comprobar cada pieza =====
%PYCMD% -c "import cryptography; print('cryptography OK', cryptography.__version__)"
%PYCMD% -c "import tkinter; print('tkinter OK')"
%PYCMD% -c "import pytest; print('pytest OK', pytest.__version__)"
echo.
echo ===== 4. Demo en consola del sistema =====
%PYCMD% main.py --consola
echo.
echo ===== 5. Pruebas =====
%PYCMD% -m pytest -v
echo.
echo Copia o toma captura de TODO lo de arriba.
pause
