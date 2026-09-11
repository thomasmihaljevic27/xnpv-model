@echo off
REM ===========================================================================
REM  xNPV sync - Desktop
REM
REM  Double-click this file to commit local changes, pull anything new from
REM  GitHub, and push. All the actual logic lives in sync.ps1 next to this
REM  file; this launcher exists only to do three things a bare .ps1 cannot:
REM
REM    1. Run on double-click. Windows opens .ps1 files in Notepad by default.
REM    2. Get past the execution policy, which blocks unsigned scripts. The
REM       -ExecutionPolicy Bypass flag applies to this one process only; it
REM       does not change any machine-wide setting.
REM    3. Keep the window open at the end so you can read the output.
REM
REM  Optional commit message:  Sync-Desktop.cmd "rebuilt draft yield curve"
REM ===========================================================================

setlocal

REM This machine's repo location. Hardcoded so the file can be copied to the
REM Desktop or pinned to the taskbar and still work from anywhere.
set "REPO=C:\Users\Thomas\Desktop\xNPV"
if exist "%REPO%\sync.ps1" goto run

REM Fallback: if that path is wrong (renamed or moved folder), use whichever
REM folder this .cmd is sitting in. Self-corrects as long as the launcher
REM stays inside the repo.
pushd "%~dp0"
set "REPO=%CD%"
popd
if exist "%REPO%\sync.ps1" goto run

echo.
echo  ERROR: could not find sync.ps1
echo.
echo  Looked in: C:\Users\Thomas\Desktop\xNPV
echo  and in:    %~dp0
echo.
echo  Fix: open this file in Notepad and correct the REPO path on the
echo       'set "REPO=..."' line to wherever the xNPV repo actually lives.
echo.
pause
exit /b 1

:run
REM -NoProfile skips your PowerShell profile, so a slow or broken profile
REM cannot interfere with the sync. %* forwards an optional commit message.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO%\sync.ps1" %*

echo.
pause
