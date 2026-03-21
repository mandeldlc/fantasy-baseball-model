from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
import numpy as np

load_dotenv()

# ================================
# CONECTAR YAHOO API
# ================================
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

# ================================
# OBTENER ROSTER DE TODOS LOS EQUIPOS
# ================================
print("Obteniendo rosters de la liga...")

bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_2025 = bateo[bateo['year'] == 2025]
pitcheo_2025 = pitcheo[pitcheo['year'] == 2025]

equipos = []
for team_id in range(1, 13):
    try:
        team = query.get_team_info(team_id=team_id)
        roster = query.get_team_roster_by_week(team_id=team_id, chosen_week=1)
        
        jugadores = [p.name.full for p in roster.players]
        
        # Score bateadores
        bat_stats = bateo_2025[bateo_2025['Name'].isin(jugadores)]
        bat_score = (
            bat_stats['woba'].mean() * 30 +
            bat_stats['xwoba'].mean() * 20 +
            bat_stats['home_run'].mean() * 0.5 +
            bat_stats['exit_velocity_avg'].mean() * 0.3
        ) if len(bat_stats) > 0 else 0

        # Score pitchers
        pit_stats = pitcheo_2025[pitcheo_2025['Name'].isin(jugadores)]
        pit_score = (
            (5 - pit_stats['p_era'].mean()) * 5 +
            (5 - pit_stats['xera'].mean()) * 3 +
            pit_stats['p_strikeout'].mean() * 0.05 +
            (0.32 - pit_stats['xwoba'].mean()) * 20
        ) if len(pit_stats) > 0 else 0

        total_score = bat_score + pit_score

        equipos.append({
            'team_id': team_id,
            'team_name': team.name.decode('utf-8') if isinstance(team.name, bytes) else team.name,
            'manager': team.managers.manager.nickname if hasattr(team.managers, 'manager') else 'N/A',
            'bat_score': round(bat_score, 2),
            'pit_score': round(pit_score, 2),
            'total_score': round(total_score, 2),
            'jugadores': len(jugadores)
        })
        print(f"  ✅ {team.name}: score {round(total_score, 2)}")

    except Exception as e:
        print(f"  ❌ Equipo {team_id}: {e}")

df = pd.DataFrame(equipos)

# ================================
# CALCULAR PROBABILIDADES
# ================================
# Normalizar scores para probabilidades
min_score = df['total_score'].min()
df['score_adj'] = df['total_score'] - min_score + 0.1
total = df['score_adj'].sum()
df['prob_camp'] = (df['score_adj'] / total * 100).round(1)

# Calcular odds americanos
def prob_to_odds(prob):
    if prob <= 0:
        return "N/A"
    if prob >= 50:
        odds = -round((prob / (100 - prob)) * 100)
        return f"{odds}"
    else:
        odds = round(((100 - prob) / prob) * 100)
        return f"+{odds}"

df['odds'] = df['prob_camp'].apply(prob_to_odds)

# Proyección inicial (basada solo en bat_score sin ajuste de temporada)
# Cargar proyección inicial si existe, si no crearla
import os
if os.path.exists('data/liga_odds_inicial.csv'):
    inicial = pd.read_csv('data/liga_odds_inicial.csv')[['team_name', 'prob_camp']]
    inicial.columns = ['team_name', 'prob_inicial']
    df = df.merge(inicial, on='team_name', how='left')
else:
    df['prob_inicial'] = df['prob_camp']
    df.to_csv('data/liga_odds_inicial.csv', index=False)
    print("✅ Proyección inicial creada")

# Tendencia
df['tendencia'] = df.apply(
    lambda r: '📈' if r['prob_camp'] > r['prob_inicial'] 
    else '📉' if r['prob_camp'] < r['prob_inicial'] 
    else '➡️', axis=1
)
df['diff'] = (df['prob_camp'] - df['prob_inicial']).round(1)

# Ordenar por probabilidad
df = df.sort_values('prob_camp', ascending=False).reset_index(drop=True)
df['rank'] = range(1, len(df) + 1)

print("\n" + "=" * 65)
print("PROBABILIDADES DE CAMPEONATO")
print("=" * 65)
print(f"{'#':>2} {'Equipo':<25} {'Prob%':>6} {'Odds':>6} {'Score':>7}")
print("-" * 65)
for _, r in df.iterrows():
    flag = "🏆" if r['rank'] == 1 else "  "
    print(f"{flag} {r['rank']:>2}. {r['team_name']:<23} {r['prob_camp']:>5.1f}% {r['odds']:>6} {r['total_score']:>7.2f}")

# Guardar
df.to_csv('data/liga_odds.csv', index=False)
print("\n✅ Guardado en data/liga_odds.csv")