@echo off

:CheckDCS
echo "Checking for DCS running"
TASKLIST /FI "IMAGENAME eq DCS.exe" 2>NUL | find /I /N "DCS.exe">NUL
IF NOT %ERRORLEVEL%==0 GOTO StartDCS
echo "DCS Already running. Checking again in 15 seconds."
timeout /t 15 /nobreak > NUL
GOTO CheckDCS

:StartDCS
echo "DCS Not running, starting it up."
xcopy C:\Users\mcdel\Dropbox\Missions "C:\Users\mcdel\Saved Games\DCS.openbeta_server\Missions" /Y
start "" "C:\Program Files\Eagle Dynamics\DCS World OpenBeta Server\bin\DCS_updater.exe"
timeout /t 15 /nobreak
GOTO CheckDCS
