# check.py -- lists which chain tables already exist. Changes nothing.
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

# Game-log database. Set GAMELOG_DB in .env (see .env.example). No default:
# a blank/wrong path would make sqlite3.connect silently create an empty file.
DB_PATH = os.environ["GAMELOG_DB"]
con = sqlite3.connect(DB_PATH)
have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
for t in ["games","skater_games","goal_events","penalty_events",   # raw scrape (must exist)
          "on_ice_skaters","shot_xg","shot_score_state",
          "score_state_factors","player_game_value"]:               # built by Scripts 1-4
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in have else "--"
    print(f"  {'OK' if t in have else 'MISSING':<8} {t:<22} {n}")
con.close()
