# import datetime
# import logging
# import json
# import re
# from pathlib import Path
# import threading
# import traceback
# from typing import List, Dict, NoReturn
#
# import asyncpg
# from lupa import LuaRuntime
# import numpy as np
# import pandas as pd
# import sqlalchemy as sa
#
# from . import db, frametimes, frametime_files, get_gcs_bucket
#
#
# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger(__name__)
# log.setLevel(level=logging.INFO)
#
#
# def parse_frametimes() -> NoReturn:
#
#     """Collect a list of frametime export files and compute framerate for each
#         line, writing the results to a database.
#     """
#     bucket = get_gcs_bucket()
#     framefiles = bucket.client.list_blobs(bucket, prefix="frametime/")
