
CD "C:\Users\mcdel\horrible-stats"

"python" "stats/logs_to_gs.py" --local-path "../Saved Games/DCS.openbeta_server/Logs/FrameTimeExport"  --local-suffix "*" --remote-subdir "frametime" --delete

"python" "stats/logs_to_gs.py" --local-path "../Saved Games/DCS.openbeta_server/SlMod/Mission Stats" --local-suffix "*.lua"  --remote-subdir "mission-stats"

"python" "stats/logs_to_gs.py" --local-path "../Documents/Tacview" --local-suffix "*.acmi" --remote-subdir "tacview"
