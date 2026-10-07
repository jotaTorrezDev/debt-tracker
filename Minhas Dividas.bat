@echo off
cd /d "%~dp0"
where pythonw >nul 2>&1 && goto rodar
where pyw >nul 2>&1 && goto rodar_py
echo Python nao encontrado neste computador.
echo Vou abrir o site para instalar. Na instalacao, MARQUE "Add python.exe to PATH".
start https://www.python.org/downloads/
pause
exit /b
:rodar
start "" pythonw app.py
exit /b
:rodar_py
start "" pyw app.py
exit /b
