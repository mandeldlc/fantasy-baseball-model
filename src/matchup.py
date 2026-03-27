from src.blend_utils import get_season
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
import numpy as np
from datetime import date, timedelta
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SEASON = get_season()

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

def get_all_matchups():
    return query.get_team_matchups(team_id=6)

def get_matchup_by_date(target_date, all_matchups):
    for m in all_matchups:
        try:
            start = date.fromisoformat(m.week_start)
            end = date.fromisoformat(m.week_end)
            if start <= target_date <= end:
                return m
        except:
            continue
    return None

def get_next_matchup(hoy, all_matchups):
    for m in all_matchups:
        try:
            start = date.fromisoformat(m.week_start)
            if start >= hoy:
                return m
        except:
            continue
    return None

def procesar_matchup(matchup):
    if matchup is None:
        return None

    teams = matchup.teams
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
        if team_id != 6:
            oponente = team

    if oponente is None:
        return None

    oponente_name = oponente.name.decode('utf-8') if isinstance(oponente.name, bytes) else oponente.name
    oponente_id = oponente.team_id
    week = matchup.week
    week_start = matchup.week_start
    week_end = matchup.week_end

    print(f"\n⚔️  Semana {week}: Dando Tabla vs {oponente_name}")
    print(f"📅 {week_start} — {week_end}")

    print(f"Obteniendo roster de {oponente_name}...")
    roster_oponente = query.get_team_roster_by_week(team_id=oponente_id, chosen_week=week)
    jugadores_oponente = [p.name.full for p in roster_oponente.players]

    bateo = pd.read_csv('data/bateo_historico.csv')
    pitcheo = pd.read_csv('data/pitcheo_historico.csv')
    bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
    bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
    pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
    pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

    # Usar data actual si hay al menos 1 entrada, sino la anterior
    # Blend: usar año actual si existe para ese jugador, sino el más reciente disponible
    SEASON_local = get_season()
    bateo_curr = bateo[bateo['year'] == SEASON_local].copy()
    pitcheo_curr = pitcheo[pitcheo['year'] == SEASON_local].copy()

    # Para jugadores sin data 2026, agregar su data más reciente
    bat_nombres_2026 = set(bateo_curr['Name']) if len(bateo_curr) > 0 else set()
    pit_nombres_2026 = set(pitcheo_curr['Name']) if len(pitcheo_curr) > 0 else set()

    bat_prev = bateo[bateo['year'] == SEASON_local - 1].copy()
    pit_prev = pitcheo[pitcheo['year'] == SEASON_local - 1].copy()

    bat_faltantes = bat_prev[~bat_prev['Name'].isin(bat_nombres_2026)]
    pit_faltantes = pit_prev[~pit_prev['Name'].isin(pit_nombres_2026)]

    bateo_curr = pd.concat([bateo_curr, bat_faltantes], ignore_index=True)
    pitcheo_curr = pd.concat([pitcheo_curr, pit_faltantes], ignore_index=True)

    mi_roster = pd.read_csv('data/roster.csv')
    mis_jugadores = mi_roster['Name'].tolist()

    def calc_bat_stats(jugadores, label):
        stats = bateo_curr[bateo_curr['Name'].isin(jugadores)]
        if len(stats) == 0:
            return {}
        return {
            'equipo': label,
            'jugadores': len(stats),
            'HR_avg': round(stats['home_run'].mean(), 1),
            'OPS': round(stats['on_base_plus_slg'].mean(), 3),
            'wOBA': round(stats['woba'].mean(), 3),
            'xwOBA': round(stats['xwoba'].mean(), 3),
            'EV': round(stats['exit_velocity_avg'].mean(), 1),
            'Barrel%': round(stats['barrel_batted_rate'].mean(), 1),
        }

    def calc_pit_stats(jugadores, label):
        stats = pitcheo_curr[pitcheo_curr['Name'].isin(jugadores)]
        if len(stats) == 0:
            return {}
        return {
            'equipo': label,
            'jugadores': len(stats),
            'ERA': round(stats['p_era'].mean(), 2),
            'xERA': round(stats['xera'].mean(), 2),
            'Ks': round(stats['p_strikeout'].mean(), 1),
            'xwOBA': round(stats['xwoba'].mean(), 3),
            'EV_against': round(stats['exit_velocity_avg'].mean(), 1),
        }

    mis_bat = calc_bat_stats(mis_jugadores, 'Dando Tabla')
    opp_bat = calc_bat_stats(jugadores_oponente, oponente_name)
    mis_pit = calc_pit_stats(mis_jugadores, 'Dando Tabla')
    opp_pit = calc_pit_stats(jugadores_oponente, oponente_name)

    def calc_team_score(bat, pit):
        score = 0
        # Si no hay stats usar valores promedio de la liga
        score += bat.get('wOBA', 0.320) * 30
        score += bat.get('xwOBA', 0.320) * 20
        score += bat.get('HR_avg', 15) * 0.5
        score += bat.get('Barrel%', 8) * 0.3
        score += bat.get('EV', 88) * 0.2
        score += (5 - pit.get('ERA', 4.0)) * 5
        score += (5 - pit.get('xERA', 4.0)) * 3
        score += pit.get('Ks', 100) * 0.05
        score += (0.32 - pit.get('xwOBA', 0.320)) * 20
        return max(score, 0.1)

    mi_score = calc_team_score(mis_bat, mis_pit)
    opp_score = calc_team_score(opp_bat, opp_pit)
    total_score = mi_score + opp_score

    prob_ganar = round((mi_score / total_score) * 100, 1)
    prob_perder = round(100 - prob_ganar, 1)

    def score_to_odds(prob):
        if prob >= 50:
            return f"-{round((prob / (100 - prob)) * 100)}"
        else:
            return f"+{round(((100 - prob) / prob) * 100)}"

    print(f"🎯 Prob. ganar: {prob_ganar}% ({score_to_odds(prob_ganar)})")

    return {
        'semana': week,
        'oponente': oponente_name,
        'oponente_id': int(oponente_id),
        'week_start': str(week_start),
        'week_end': str(week_end),
        'mis_bat': mis_bat,
        'opp_bat': opp_bat,
        'mis_pit': mis_pit,
        'opp_pit': opp_pit,
        'prob_ganar': prob_ganar,
        'prob_perder': prob_perder,
        'odds_ganar': score_to_odds(prob_ganar),
        'odds_perder': score_to_odds(prob_perder)
    }

# ================================
# PROCESAR SEMANA ACTUAL Y SIGUIENTE
# ================================
hoy = date.today()
print("Cargando todos los matchups...")
all_matchups = get_all_matchups()

print("Obteniendo matchup semana actual...")
matchup_actual = get_matchup_by_date(hoy, all_matchups)

if matchup_actual is None:
    print("No hay matchup esta semana, usando el próximo disponible...")
    matchup_actual = get_next_matchup(hoy, all_matchups)

resultado_actual = procesar_matchup(matchup_actual)

print("\nObteniendo matchup semana siguiente...")
if matchup_actual is not None:
    fin_semana_actual = date.fromisoformat(str(matchup_actual.week_end))
    inicio_semana_siguiente = fin_semana_actual + timedelta(days=1)
    matchup_siguiente = get_matchup_by_date(inicio_semana_siguiente, all_matchups)
else:
    matchup_siguiente = None

resultado_siguiente = procesar_matchup(matchup_siguiente)

with open('data/matchup_semana.json', 'w') as f:
    json.dump(resultado_actual, f, indent=2)

if resultado_siguiente:
    with open('data/matchup_siguiente.json', 'w') as f:
        json.dump(resultado_siguiente, f, indent=2)

print("\n✅ Guardado en data/matchup_semana.json y data/matchup_siguiente.json")

# ================================
# PROCESAR TODAS LAS SEMANAS
# ================================
print("\nProcesando todas las semanas de la temporada...")
todas_semanas = []

for m in all_matchups:
    try:
        resultado = procesar_matchup(m)
        if resultado:
            todas_semanas.append(resultado)
            print(f"  ✅ Semana {resultado['semana']}: vs {resultado['oponente']} — {resultado['prob_ganar']}%")
    except Exception as e:
        print(f"  ❌ Error semana: {e}")

with open('data/matchup_temporada.json', 'w') as f:
    json.dump(todas_semanas, f, indent=2)

print(f"\n✅ {len(todas_semanas)} semanas guardadas en data/matchup_temporada.json")