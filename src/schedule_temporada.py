from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
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

print("Obteniendo schedule completo de la temporada...")

matchups = query.get_team_matchups(team_id=6)

schedule = []
for m in matchups:
    try:
        semana = m.week
        week_start = m.week_start
        week_end = m.week_end
        status = m.status
        is_playoffs = m.is_playoffs

        # Obtener oponente
        oponente = None
        oponente_id = None
        for team in m.teams:
            t = team['team'] if isinstance(team, dict) else team
            team_id = t.team_id if hasattr(t, 'team_id') else t.get('team_id')
            if team_id != 6:
                oponente = t.name if hasattr(t, 'name') else t.get('name', '')
                if isinstance(oponente, bytes):
                    oponente = oponente.decode('utf-8')
                oponente_id = team_id

        # Cargar probabilidades de campeonato
        try:
            odds = pd.read_csv('data/liga_odds.csv')
            opp_prob = odds[odds['team_name'] == oponente]['prob_camp'].values
            mi_prob = odds[odds['team_id'] == 6]['prob_camp'].values
            opp_prob = float(opp_prob[0]) if len(opp_prob) > 0 else 50.0
            mi_prob = float(mi_prob[0]) if len(mi_prob) > 0 else 50.0
        except:
            opp_prob = 50.0
            mi_prob = 50.0

        # Probabilidad de ganar este matchup basado en roster score
        try:
            odds_df = pd.read_csv('data/liga_odds.csv')
            mi_roster = odds_df[odds_df['team_id'] == 6]['roster_score'].values[0]
            opp_roster = odds_df[odds_df['team_name'] == oponente]['roster_score'].values
            opp_roster = float(opp_roster[0]) if len(opp_roster) > 0 else 70.0
            total = mi_roster + opp_roster
            prob_ganar = round((mi_roster / total) * 100, 1) if total > 0 else 50.0
            prob_perder = round(100 - prob_ganar, 1)
        except:
            prob_ganar = 50.0
            prob_perder = 50.0

        schedule.append({
            'semana': semana,
            'week_start': str(week_start),
            'week_end': str(week_end),
            'oponente': oponente,
            'oponente_id': oponente_id,
            'status': status,
            'is_playoffs': is_playoffs,
            'prob_ganar': prob_ganar,
            'prob_perder': prob_perder,
            'opp_prob_camp': opp_prob,
            'mi_prob_camp': mi_prob
        })

        dificultad = '🔴 Difícil' if opp_prob > mi_prob * 1.2 else '🟢 Fácil' if mi_prob > opp_prob * 1.2 else '🟡 Parejo'
        playoffs_tag = '🏆 PLAYOFFS' if is_playoffs else ''
        print(f"  Semana {semana}: vs {oponente} {dificultad} {playoffs_tag} ({week_start})")

    except Exception as e:
        print(f"  ❌ Error semana: {e}")

df = pd.DataFrame(schedule).sort_values('semana')
df.to_csv('data/schedule_temporada.csv', index=False)

print(f"\n✅ {len(df)} matchups guardados en data/schedule_temporada.csv")
print(f"   Semanas: {df['semana'].min()} — {df['semana'].max()}")
print(f"   Playoffs: {df['is_playoffs'].sum()} semanas")