from stats.read_stats import *


STATS_PATH = Path("C:/Users/mcdel/Dropbox/dcs-stats/Mission Stats/")
file_test = STATS_PATH.joinpath("Operation Snowfox v122- Jan 17, 2020 at 20 14 45.lua")
df = read_lua_table(file_test)
data = main(stats_path=STATS_PATH, max_parse=20)
