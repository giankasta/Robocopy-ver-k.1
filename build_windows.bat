@echo off
setlocal
cd /d "%~dp0"

py -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller non trovato. Installazione in corso...
    py -m pip install --user pyinstaller
    if errorlevel 1 goto :error
)

py -m PyInstaller --noconfirm --clean --onefile --windowed --name CopiaFotoIPhone --add-data "iphone_mtp_copy.ps1;." robocopy_gui.py
if errorlevel 1 goto :error

echo.
echo Eseguibile creato: dist\CopiaFotoIPhone.exe
pause
exit /b 0

:error
echo.
echo Creazione non riuscita. Controlla Python, pip e la connessione Internet.
pause
exit /b 1