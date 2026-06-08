# test_db.py
from dotenv import load_dotenv
load_dotenv()

import os
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

from agent.tools.mysql_tools import get_team_matches
import json

result = get_team_matches("Switzerland", 5)
print(json.loads(result))