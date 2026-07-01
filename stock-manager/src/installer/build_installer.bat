@echo off
REM ================================================================
REM  Stock Manager Pro — Full Build + Installer Script
REM  Run from the REPO ROOT:  installer\build_installer.bat
REM ================================================================
setlocal enabledelayedexpansion

set SRC_DIR=%~dp0..\src
set ISS_FILE=%~dp0StockManagerPro.iss
set OUTPUT_DIR=%~dp0Output

REM ── Read version from the single source of truth (version.py) ──
for /f "delims=" %%v in ('python -c "import re;print(re.search(r'APP_VERSION\s*=\s*\"([^\"]+)\"',open(r'%SRC_DIR%\files\app\core\version.py',encoding='utf-8').read()).group(1))"') do set APP_VERSION=%%v
if "%APP_VERSION%"=="" ( echo  ERROR: could not read APP_VERSION from version.py & exit /b 1 )

echo.
echo ============================================================
echo   Stock Manager Pro v%APP_VERSION%  —  Build ^& Package
echo ============================================================
echo.

REM ── 1. Python check ──────────────────────────────────────────
echo [1/4] Checking Python + PyInstaller...
python --version >nul 2>&1
if errorlevel 1 ( echo  ERROR: Python not found. Activate your venv first. & exit /b 1 )
pyinstaller --version >nul 2>&1
if errorlevel 1 ( echo  ERROR: PyInstaller not found. Run: pip install pyinstaller & exit /b 1 )
echo        OK

REM ── 2. PyInstaller build ─────────────────────────────────────
echo [2/4] Running PyInstaller...
pushd "%SRC_DIR%"
pyinstaller StockManagerPro.spec --noconfirm --clean
if errorlevel 1 ( echo  ERROR: PyInstaller failed. & popd & exit /b 1 )
popd
echo        OK — dist\StockManagerPro ready

REM ── 3. Verify EXE ────────────────────────────────────────────
echo [3/4] Verifying build output...
if not exist "%SRC_DIR%\dist\StockManagerPro\StockManagerPro.exe" (
    echo  ERROR: StockManagerPro.exe not found in dist\StockManagerPro\
    exit /b 1
)
echo        OK

REM ── 4. Inno Setup 7 compile ──────────────────────────────────
echo [4/4] Compiling installer with Inno Setup 7...

set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 7\iscc.exe" set ISCC="C:\Program Files (x86)\Inno Setup 7\iscc.exe"
if exist "C:\Program Files\Inno Setup 7\iscc.exe"       set ISCC="C:\Program Files\Inno Setup 7\iscc.exe"

REM Fall back to PATH
if %ISCC%=="" (
    where iscc >nul 2>&1
    if not errorlevel 1 ( set ISCC=iscc ) else (
        echo  ERROR: Inno Setup 7 not found.
        echo         Install from https://jrsoftware.org/isdl.php
        exit /b 1
    )
)

REM ── Regenerate wizard images stamped with the current version ──
python "%~dp0make_wizard_banner.py" %APP_VERSION%
if errorlevel 1 ( echo  ERROR: wizard image generation failed. & exit /b 1 )

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
%ISCC% /DAppVersion=%APP_VERSION% "%ISS_FILE%"
if errorlevel 1 ( echo  ERROR: Inno Setup compile failed. & exit /b 1 )

echo.
echo ============================================================
echo   SUCCESS!
echo   Output: %OUTPUT_DIR%\StockManagerPro-%APP_VERSION%-setup.exe
echo ============================================================
echo.
explorer "%OUTPUT_DIR%"
endlocal
