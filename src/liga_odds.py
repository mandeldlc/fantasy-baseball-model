from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os
import pandas as pd
import numpy as np

load_dotenv()

SEASON = date.today().year

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

print("Obteniendo datos de la liga...")

bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_curr = bateo[bateo['year'] == SEASON]
pitcheo_curr = pitcheo[pitcheo['year'] == SEASON]
if len(bateo_curr) < 50:
    bateo_curr = bateo[bateo['year'] == SEASON - 1]
if len(pitcheo_curr) < 50:
    pitcheo_curr = pitcheo[pitcheo['year'] == SEASON - 1]

equipos = []
for team_id in range(1, 13):
    try:
        team = query.get_team_info(team_id=team_id)
        roster = query.get_team_roster_by_week(team_id=team_id, chosen_week=1)
        standings = query.get_team_standings(team_id=team_id)

        jugadores = [p.name.full for p in roster.players]

        # Score bateadores
        bat_stats = bateo_curr[bateo_curr['Name'].isin(jugadores)]
        bat_score = (
            bat_stats['woba'].mean() * 30 +
            bat_stats['xwoba'].mean() * 20 +
            bat_stats['home_run'].mean() * 0.5 +
            bat_stats['exit_velocity_avg'].mean() * 0.3
        ) if len(bat_stats) > 0 else 0

        # Score pitchers
        pit_stats = pitcheo_curr[pitcheo_curr['Name'].isin(jugadores)]
        pit_score = (
            (5 - pit_stats['p_era'].mean()) * 5 +
            (5 - pit_stats['xera'].mean()) * 3 +
            pit_stats['p_strikeout'].mean() * 0.05 +
            (0.32 - pit_stats['xwoba'].mean()) * 20
        ) if len(pit_stats) > 0 else 0

        roster_score = bat_score + pit_score

        # Record actual W-L-T
        try:
            wins = standings.outcome_totals.wins
            losses = standings.outcome_totals.losses
            ties = standings.outcome_totals.ties
            total_games = wins + losses + ties
            # T vale 0.5W
            win_pct = (wins + ties * 0.5) / total_games if total_games > 0 else 0.5
        except:
            wins, losses, ties, win_pct = 0, 0, 0, 0.5

        # Felo score
        try:
            managers = team.managers
            if isinstance(managers, list):
                manager_obj = managers[0]
            elif hasattr(managers, 'manager'):
                manager_obj = managers.manager
            else:
                manager_obj = managers
            felo_score = int(manager_obj.felo_score) if hasattr(manager_obj, 'felo_score') and manager_obj.felo_score else 600
            manager_name = str(manager_obj.nickname) if hasattr(manager_obj, 'nickname') else 'N/A'
        except:
            felo_score = 600
            manager_name = 'N/A'

        team_name = team.name.decode('utf-8') if isinstance(team.name, bytes) else team.name

        equipos.append({
            'team_id': team_id,
            'team_name': team_name,
            'manager': manager_name,
            'bat_score': round(bat_score, 2),
            'pit_score': round(pit_score, 2),
            'roster_score': round(roster_score, 2),
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'win_pct': round(win_pct, 3),
            'felo_score': felo_score,
            'jugadores': len(jugadores)
        })
        print(f"  ✅ {team_name}: roster={round(roster_score,1)} W-L-T={wins}-{losses}-{ties} felo={felo_score}")

    except Exception as e:
        print(f"  ❌ Equipo {team_id}: {e}")

df = pd.DataFrame(equipos)

# ================================
# CALCULAR PROBABILIDADES PONDERADAS
# 50% roster, 30% record W-L-T, 20% historial felo
# T vale 0.5W en el win_pct
# ================================
def normalize(series):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return series * 0 + 0.5
    return (series - mn) / (mx - mn)

# Recalcular win_pct con T = 0.5W
df['win_pct'] = df.apply(
    lambda r: (r['wins'] + r['ties'] * 0.5) / (r['wins'] + r['losses'] + r['ties'])
    if (r['wins'] + r['losses'] + r['ties']) > 0 else 0.5, axis=1
)

df['roster_norm'] = normalize(df['roster_score'])
df['winpct_norm'] = normalize(df['win_pct'])
df['felo_norm'] = normalize(df['felo_score'])

df['score_compuesto'] = (
    df['roster_norm'] * 0.50 +
    df['winpct_norm'] * 0.30 +
    df['felo_norm'] * 0.20
)

total = df['score_compuesto'].sum()
df['prob_camp'] = (df['score_compuesto'] / total * 100).round(1)

def prob_to_odds(prob):
    if prob <= 0:
        return "N/A"
    if prob >= 50:
        return str(-round((prob / (100 - prob)) * 100))
    else:
        return f"+{round(((100 - prob) / prob) * 100)}"

df['odds'] = df['prob_camp'].apply(prob_to_odds)

# Proyección inicial
if os.path.exists('data/liga_odds_inicial.csv'):
    inicial = pd.read_csv('data/liga_odds_inicial.csv')[['team_name', 'prob_camp']]
    inicial.columns = ['team_name', 'prob_inicial']
    df = df.merge(inicial, on='team_name', how='left')
    df['prob_inicial'] = df['prob_inicial'].fillna(df['prob_camp'])
else:
    df['prob_inicial'] = df['prob_camp']
    df.to_csv('data/liga_odds_inicial.csv', index=False)
    print("✅ Proyección inicial creada")

df['tendencia'] = df.apply(
    lambda r: '📈' if r['prob_camp'] > r['prob_inicial']
    else '📉' if r['prob_camp'] < r['prob_inicial']
    else '➡️', axis=1
)
df['diff'] = (df['prob_camp'] - df['prob_inicial']).round(1)

df = df.sort_values('prob_camp', ascending=False).reset_index(drop=True)
df['rank'] = range(1, len(df) + 1)

print("\n" + "=" * 75)
print("PROBABILIDADES DE CAMPEONATO — MODELO COMPLETO")
print("=" * 75)
print(f"{'#':>2} {'Equipo':<28} {'Prob%':>6} {'Odds':>6} {'W-L-T':>7} {'Felo':>5} {'Tend':>5}")
print("-" * 75)
for _, r in df.iterrows():
    flag = "🏆" if r['rank'] == 1 else "  "
    wlt = f"{int(r['wins'])}-{int(r['losses'])}-{int(r['ties'])}"
    print(f"{flag} {r['rank']:>2}. {r['team_name']:<26} {r['prob_camp']:>5.1f}% {r['odds']:>6} {wlt:>7} {int(r['felo_score']):>5} {r['tendencia']:>5}")

df.to_csv('data/liga_odds.csv', index=False)
print("\n✅ Guardado en data/liga_odds.csv")