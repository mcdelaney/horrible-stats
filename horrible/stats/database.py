from starlette.config import Config
import databases

config = Config('.env')
DATABASE_URL = config('DATABASE_URL')
db = databases.Database(DATABASE_URL)
