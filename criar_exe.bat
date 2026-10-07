@echo off
cd /d "%~dp0"
python -m pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name MinhasDividas app.py
copy /y dist\MinhasDividas.exe . >nul
rmdir /s /q build dist
del MinhasDividas.spec
echo.
echo Pronto! Use o arquivo MinhasDividas.exe (pode criar atalho na area de trabalho).
pause
