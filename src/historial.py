from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
from datetime import date
import json

load_dotenv()

query = YahooFantasySportsQuery(
    league_id="31891",
    game_code="mlb",
    game_id=469,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    yahoo_access_token_json=None,
    env_file_location=Path("."),
    save_token_data_to_env_file=True
)

print("Obteniendo historial de matchups...")

matchups = query.get_team_matchups(team_id=6)
historial = []

for m in matchups:
    try:
        # Solo procesar semanas pasadas o en curso
        week_end = date.fromisoformat(m.week_end)
        if week_end > date.today():
            continue

        teams = m.teams
        mi_team = None
        oponente = None

        for t in teams:
            if isinstance(t, dict):
                team = t.get('team', t)
            else:
                team = t
            try:
                team_id = team.team_id
            except:
                team_id = team.get('team_id')
            if team_id == 6:
                mi_team = team
            else:
                oponente = team

        if mi_team is None or oponente is None:
            continue

        oponente_name = oponente.name.decode('utf-8') if isinstance(oponente.name, bytes) else oponente.name

        # Puntos
        try:
            mis_puntos = float(mi_team.team_points.total)
            opp_puntos = float(oponente.team_points.total)
        except:
            mis_puntos = 0.0
            opp_puntos = 0.0

        # Resultado
        if mis_puntos > opp_puntos:
            resultado = 'W'
        elif mis_puntos < opp_puntos:
            resultado = 'L'
        else:
            resultado = 'T'

        historial.append({
            'semana': m.week,
            'week_start': m.week_start,
            'week_end': m.week_end,
            'oponente': oponente_name,
            'mis_puntos': mis_puntos,
            'opp_puntos': opp_puntos,
            'resultado': resultado
        })

        print(f"  Semana {m.week}: vs {oponente_name} — {mis_puntos} vs {opp_puntos} → {resultado}")

    except Exception as e:
        print(f"  ❌ Semana {m.week}: {e}")

df = pd.DataFrame(historial)

if len(df) == 0:
    print("No hay semanas completadas aún — guardando historial vacío")
    df = pd.DataFrame(columns=['semana', 'week_start', 'week_end', 'oponente', 'mis_puntos', 'opp_puntos', 'resultado'])

df.to_csv('data/historial_matchups.csv', index=False)
print(f"\n✅ Guardado en data/historial_matchups.csv — {len(df)} semanas")