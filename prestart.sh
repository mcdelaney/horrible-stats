#! /usr/bin/env bash

python << EOF
import asyncio
import databases
from tacview_client import db as tac_db
from horrible import read_stats
from horrible.database import DATABASE_URL

async def prestart():
    db = databases.Database(DATABASE_URL)
    await db.connect()
    tac_db.create_tables()

print('Populating weapondb and creating tacview tables...')
asyncio.run(prestart())
print('Done')
EOF