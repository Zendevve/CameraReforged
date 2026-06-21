@echo off
setlocal

REM ==========================================================
REM  Drag-and-drop launcher for patch_camera.py
REM  Usage: drag WoW.exe onto this .bat file (or its shortcut)
REM ==========================================================

if "%~1"=="" (
    echo.
    echo   Drag your WoW.exe file onto this .bat file to patch
    echo   the camera height. Nothing has been changed.
    echo.
    pause
    exit /b 1
)

set "TARGET=%~1"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%patch_camera.py"

if not exist "%SCRIPT_PATH%" (
    echo.
    echo   ERROR: Could not find patch_camera.py next to this .bat file.
    echo   Make sure both files are in the same folder:
    echo     %SCRIPT_DIR%
    echo.
    pause
    exit /b 1
)

echo.
echo   Target:  %TARGET%
echo   Script:  %SCRIPT_PATH%
echo.

set "PORTABLE_PY=%SCRIPT_DIR%python_portable\python.exe"

where python >nul 2>nul
if %errorlevel%==0 (
    python "%SCRIPT_PATH%" "%TARGET%" --apply
    goto :done
)

where py >nul 2>nul
if %errorlevel%==0 (
    py "%SCRIPT_PATH%" "%TARGET%" --apply
    goto :done
)

if exist "%PORTABLE_PY%" (
    "%PORTABLE_PY%" "%SCRIPT_PATH%" "%TARGET%" --apply
    goto :done
)

echo.
echo   Python was not found on this PC.
echo.
echo   Would you like to automatically download a lightweight, portable
echo   version of Python (~10MB) to run this script?
echo.
set /p "CHOICE=  Download and use portable Python? (Y/N): "
if /i "%CHOICE%"=="Y" goto :download_python
if /i "%CHOICE%"=="Yes" goto :download_python

echo.
echo   ERROR: Python was not found on this PC.
echo   Install it from https://www.python.org/downloads/
echo   and make sure to check "Add python.exe to PATH" during setup.
echo.
pause
exit /b 1

:download_python
echo.
echo   Detecting system architecture...
set "PYTHON_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-win32.zip"
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "PYTHON_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
if "%PROCESSOR_ARCHITEW6432%"=="AMD64" set "PYTHON_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"

echo   Downloading portable Python from:
echo     %PYTHON_URL%
echo.

curl -L -o "%SCRIPT_DIR%python_portable.zip" "%PYTHON_URL%"
if not %errorlevel%==0 (
    echo.
    echo   ERROR: Failed to download Python zip.
    echo   Please check your internet connection or install Python manually.
    echo.
    pause
    exit /b 1
)

echo.
echo   Extracting portable Python to:
echo     %SCRIPT_DIR%python_portable ...
powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%python_portable.zip' -DestinationPath '%SCRIPT_DIR%python_portable' -Force"
if not %errorlevel%==0 (
    echo.
    echo   ERROR: Failed to extract Python zip.
    echo   Please install Python manually.
    echo.
    del "%SCRIPT_DIR%python_portable.zip" >nul 2>nul
    pause
    exit /b 1
)

del "%SCRIPT_DIR%python_portable.zip" >nul 2>nul
echo.
echo   Done! Running camera patcher...
echo.

if exist "%PORTABLE_PY%" (
    "%PORTABLE_PY%" "%SCRIPT_PATH%" "%TARGET%" --apply
) else (
    echo   ERROR: python.exe not found in extracted folder.
    pause
    exit /b 1
)

:done
echo.
pause
