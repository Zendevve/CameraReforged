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

echo.
echo   ERROR: Python was not found on this PC.
echo   Install it from https://www.python.org/downloads/
echo   and make sure to check "Add python.exe to PATH" during setup.
echo.
pause
exit /b 1

:done
echo.
pause
