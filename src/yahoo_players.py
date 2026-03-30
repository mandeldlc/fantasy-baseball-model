from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import normalizar_nombre

load_dotenv()

query = YahooFantasySportsQuery(
    league_id='31891', game_code='mlb', game_id=469,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    yahoo_access_token_json=None,
    env_file_location=Path('.'), save_token_data_to_env_file=True
)

print("Descargando todos los jugadores de Yahoo Fantasy...")

todos = []
start = 0
batch = 25

while True:
    try:
        players = query.get_league_players(player_count_limit=batch, player_count_start=start)
        if not players or len(players) == 0:
            break
        for p in players:
            todos.append({
                'yahoo_name': p.name.full,
                'yahoo_norm': normalizar_nombre(p.name.full),
                'position': p.display_position,
                'status': str(p.status) if p.status else 'active',
                'ownership': str(p.ownership_type) if hasattr(p, 'ownership_type') else 'unknown'
            })
        print(f"  Descargados: {len(todos)} jugadores...")
        if len(players) < batch:
            break
        start += batch
    except Exception as e:
        print(f"  Error en batch {start}: {e}")
        break

df = pd.DataFrame(todos)
df.to_csv('data/yahoo_players.csv', index=False)
print(f"\n✅ {len(df)} jugadores guardados en data/yahoo_players.csv")
print(df['position'].value_counts().head(10))