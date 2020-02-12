@echo off

:CheckDCS
echo "Checking for DCS running"
TASKLIST /FI "IMAGENAME eq DCS.exe" 2>NUL | find /I /N "DCS.exe">NUL
IF NOT %ERRORLEVEL%==0 GOTO StartDCS
echo "DCS Already running. Checking again in 15 seconds."

echo "Checking for SRS running"
TASKLIST /FI "IMAGENAME eq SR-Server.exe" 2>NUL | find /I /N "SR-Server.exe">NUL
IF NOT %ERRORLEVEL%==0 GOTO StartSRS
echo "SRS Already running. Checking again in 15 seconds."

timeout /t 15 /nobreak > NUL
GOTO CheckDCS

:StartDCS
echo "DCS Not running, starting it up."
python "C:\\Users\mcdel\horrible-stats\scripts\upload_dcs_log.py"
xcopy C:\Users\mcdel\Dropbox\Missions "C:\Users\mcdel\Saved Games\DCS.openbeta_server\Missions" /Y
start "" "C:\Program Files\Eagle Dynamics\DCS World OpenBeta Server\bin\DCS_updater.exe"
timeout /t 15 /nobreak
GOTO CheckDCS

:StartSRS
echo "SRS Not running, starting it up."
start "" "C:\Program Files (x86)\DCS-SimpleRadio-Standalone\SR-Server.exe"
timeout /t 15 /nobreak
GOTO CheckDCS
