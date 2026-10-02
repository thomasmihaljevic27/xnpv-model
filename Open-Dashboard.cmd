@echo off
REM ===========================================================================
REM  xNPV player dashboard - OPEN the last build (nothing is re-run)
REM
REM  Double-click this file to open 30_OUTPUT\player_dashboard.html as it was
REM  last built, and see when that was. To re-run the chain and rebuild it
REM  first, double-click Update-Dashboard.cmd instead (about 10 minutes).
REM
REM  The dashboard records its own build (commit, scripts, time) in its
REM  header, so an old build says so when it opens.
REM ===========================================================================

setlocal

REM The folder this file sits in, then the two machines' repo locations, so a
REM copy pinned to the taskbar or Desktop still finds the repo.
set "REPO=%~dp0"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto found
set "REPO=C:\Users\Thomas\Desktop\xNPV\"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto found
set "REPO=C:\Users\thoma\Desktop\xNPV\"
if exist "%REPO%20_CODE\dashboard_refresh.py" goto found

echo.
echo  ERROR: could not find the xNPV repo
echo  Looked in: %~dp0
echo             C:\Users\Thomas\Desktop\xNPV\
echo             C:\Users\thoma\Desktop\xNPV\
echo.
pause
exit /b 1

:found
set "DASH=%REPO%30_OUTPUT\player_dashboard.html"
if exist "%DASH%" goto open

echo.
echo  No dashboard has been built on this machine yet:
echo    %DASH%
echo  Double-click Update-Dashboard.cmd to build it.
echo.
pause
exit /b 1

:open
for %%F in ("%DASH%") do echo  Opening the dashboard last built %%~tF
start "" "%DASH%"
