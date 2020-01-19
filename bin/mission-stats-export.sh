#!/bin/bash
python3 stats/logs_to_gs.py --local-path "/mnt/c/users/mcdel/Saved Games/DCS.openbeta_server/SlMod/Mission Stats" --local-suffix "*.lua"  --remote-subdir "mission-stats"
