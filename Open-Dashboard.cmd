@echo off
REM ===========================================================================
REM  xNPV player dashboard - refresh everything, then open
REM
REM  Double-click this file. It re-runs every script the dashboard depends on,
REM  using the code as it is on this machine now, builds the dashboard, and
REM  opens it in your browser. It stops (and does not open anything) if a
REM  step fails a guard, or if GitHub has newer scripts than this machine.
REM
REM  The logic lives in 20_CODE\dashboard_refresh.py. This launcher only finds
REM  the repo, runs it, and keeps the window open so you can read the result.
REM
REM  Options pass straight through, e.g.
REM    Open-Dashboard.cmd --refresh-draft   also re-pull the NHL draft records
REM    Open-Dashboard.cmd --allow-behind    run even if GitHub has newer commits
REM
REM  To reopen the last build without re-running anything, open
REM  30_OUTPUT\player_dashboard.html directly.
REM ===========================================================================

setlocal

REM The folder this file sits in, then the two machines' repo locations, so a
REM copy pinned to the taskbar or Desktop still finds the repo.
set "REPO=%~dp0"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto run
set "REPO=C:\Users\Thomas\Desktop\xNPV\"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto run
set "REPO=C:\Users\thoma\Desktop\xNPV\"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto run

echo.
echo  ERROR: could not find 20_CODE\dashboard_refresh.py
echo  Looked in: %~dp0
echo             C:\Users\Thomas\Desktop\xNPV\
echo             C:\Users\thoma\Desktop\xNPV\
echo.
pause
exit /b 1

:run
cd /d "%REPO%"
python "%REPO%20_CODE\dashboard_refresh.py" %*

echo.
pause
