from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd

load_dotenv()

CLIENT_ID = os.getenv('YAHOO_CLIENT_ID')
CLIENT_SECRET = os.getenv('YAHOO_CLIENT_SECRET')

query = YahooFantasySportsQuery(
    league_id="31891",
    game_code="mlb",
    game_id=469,
    yahoo_consumer_key=CLIENT_ID,
    yahoo_consumer_secret=CLIENT_SECRET,
    yahoo_access_token_json=None,
    env_file_location=Path("."),
    save_token_data_to_env_file=True
)

def get_roster():
    print("Obteniendo tu roster de Yahoo Fantasy...")
    roster = query.get_team_roster_by_week(team_id=6, chosen_week=1)

    jugadores = []
    for player in roster.players:
        jugadores.append({
            'Name': player.name.full,
            'Pos': player.selected_position.position,
            'Team': player.editorial_team_abbr,
            'Status': player.status if player.status else 'active'
        })

    df = pd.DataFrame(jugadores)
    df.to_csv('data/roster.csv', index=False)
    print(f"✅ Roster actualizado: {len(df)} jugadores")
    print(df.to_string(index=False))
    return df

if __name__ == "__main__":
    get_roster()