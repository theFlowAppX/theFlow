@echo off
REM =========================================================
REM build_windows.bat — Build theFlow! exe + installer
REM Run from the project folder:  build_windows.bat
REM Requirements:
REM   pip install pyinstaller PyQt6 PyQt6-Qt6 PyQt6-sip
REM   Inno Setup 6 installed
REM =========================================================

echo === Step 1: Build theFlow.exe with PyInstaller ===
python -m PyInstaller theflow.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    pause
    exit /b 1
)

echo.
echo === Step 2: Build installer with Inno Setup ===
set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo ERROR: Inno Setup not found. Install from https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
%ISCC% theflow_setup.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup failed. Check output above.
    pause
    exit /b 1
)

echo.
echo === Done! ===
echo   App:       dist\theFlow.exe
echo   Installer: dist\theFlow-0.1.0-setup.exe
pause
