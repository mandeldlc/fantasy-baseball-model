from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd

load_dotenv()
query = YahooFantasySportsQuery(
    league_id='31891', game_code='mlb', game_id=469,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    yahoo_access_token_json=None,
    env_file_location=Path('.'), save_token_data_to_env_file=True
)

print("Obteniendo jugadores de Yahoo...")
players = query.get_league_players(player_count_limit=25, player_count_start=0)
print(f"Total: {len(players)}")

for p in players[:5]:
    print(f"  {p.name.full} | Pos: {p.display_position} | Status: {p.status}")