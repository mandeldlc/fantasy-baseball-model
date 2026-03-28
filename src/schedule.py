import requests
import pandas as pd
from datetime import date, timedelta
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_curr_data

SEASON = get_season()

def get_week_dates():
    try:
        with open('data/matchup_semana.json') as f:
            matchup = json.load(f)
        return matchup['week_start'], matchup['week_end']
    except:
        hoy = date.today()
        return str(hoy), str(hoy + timedelta(days=6))

def get_team_strength():
    try:
        df = pd.read_csv('data/team_offense.csv')
        year_max = df['year'].max()
        df_recent = df[df['year'] == year_max]
        equipos = {}
        for _, row in df_recent.iterrows():
            equipos[row['team_name']] = {
                'offense_score_norm': row['offense_score_norm'],
                'woba': row['woba'],
                'xwoba': row['xwoba'],
                'dificultad': row['dificultad']
            }
        return equipos
    except:
        return {}

def get_jugadores_tomados():
    """Cargar todos los jugadores tomados en la liga con su equipo"""
    try:
        tomados = pd.read_csv('data/jugadores_tomados.csv')
        return dict(zip(tomados['yahoo_name'], tomados.get('team_name', ['?'] * len(tomados))))
    except:
        return {}

def get_pitcher_opponents(start_date, end_date, team_strength):
    url = (f"https://statsapi.mlb.com/api/v1/schedule"
           f"?sportId=1&startDate={start_date}&endDate={end_date}"
           f"&gameType=R&hydrate=probablePitcher")
    r = requests.get(url)
    data = r.json()
    pitcher_info = {}

    for dia in data.get('dates', []):
        fecha = dia['date']
        for juego in dia.get('games', []):
            away_team = juego['teams']['away']['team']['name']
            home_team = juego['teams']['home']['team']['name']
            for lado, opp in [('away', home_team), ('home', away_team)]:
                pitcher = juego['teams'][lado].get('probablePitcher')
                if pitcher:
                    nombre = pitcher.get('fullName', '')
                    if nombre:
                        opp_data = team_strength.get(opp, {})
                        offense_score = opp_data.get('offense_score_norm', 50.0)
                        dificultad = opp_data.get('dificultad', '🟡 Normal')
                        favorabilidad = round(100 - offense_score, 1)

                        if nombre not in pitcher_info:
                            pitcher_info[nombre] = {'starts': [], 'total_starts': 0}
                        pitcher_info[nombre]['starts'].append({
                            'fecha': fecha,
                            'oponente': opp,
                            'offense_score': offense_score,
                            'dificultad': dificultad,
                            'favorabilidad': favorabilidad,
                            'woba_opp': opp_data.get('woba', 0.310),
                        })
                        pitcher_info[nombre]['total_starts'] += 1

    return pitcher_info

def get_pitcher_stats():
    """Cargar stats de pitcheo histórico con blend"""
    pitcheo = pd.read_csv('data/pitcheo_historico.csv')
    pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
    pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

    pit_curr = pitcheo[pitcheo['year'] == SEASON].copy()
    pit_prev = pitcheo[pitcheo['year'] == SEASON - 1].copy()
    pit_faltantes = pit_prev[~pit_prev['Name'].isin(set(pit_curr['Name']))]
    return pd.concat([pit_curr, pit_faltantes], ignore_index=True)

def build_row(nombre, pitcher_info, pit_stats, tomados, roster_names):
    info = pitcher_info.get(nombre, {})
    starts = info.get('total_starts', 0)
    oponentes = info.get('starts', [])
    fav_promedio = round(sum([s['favorabilidad'] for s in oponentes]) / len(oponentes), 1) if oponentes else 50.0
    opp_str = ' | '.join([
        f"{s['fecha']} vs {s['oponente']} ({s['dificultad']}) wOBA:{s['woba_opp']:.3f}"
        for s in oponentes
    ])

    # Stats del pitcher
    stats = pit_stats[pit_stats['Name'] == nombre]
    era  = round(stats['p_era'].values[0], 2) if len(stats) > 0 else 0
    xera = round(stats['xera'].values[0], 2) if len(stats) > 0 else 0
    ks   = int(stats['p_strikeout'].values[0]) if len(stats) > 0 else 0
    xwoba = round(stats['xwoba'].values[0], 3) if len(stats) > 0 else 0

    # Favorabilidad unificada — combina offense score del oponente + stats del pitcher
    if era > 0 and xera > 0:
        pitcher_quality = max(0, (5 - xera) * 10)
        fav_unificada = round((fav_promedio * 0.6 + pitcher_quality * 0.4), 1)
    else:
        fav_unificada = fav_promedio

    # Dónde está el jugador
    if nombre in roster_names:
        ubicacion = "🏟️ Mi Roster"
    elif nombre in tomados:
        ubicacion = f"⚔️ Rival"
    else:
        ubicacion = "🔓 Waiver"

    return {
        'Name': nombre,
        'Ubicacion': ubicacion,
        'Starts': starts,
        'Doble_Start': '⭐ DOBLE' if starts >= 2 else '➡️ Simple' if starts == 1 else '❌ Sin start',
        'Favorabilidad': fav_unificada,
        'ERA': era,
        'xERA': xera,
        'Ks': ks,
        'xwOBA': xwoba,
        'Oponentes': opp_str if opp_str else 'Sin start asignado',
    }

# ================================
# MAIN
# ================================
print("Analizando schedule de la semana...")

week_start, week_end = get_week_dates()
print(f"Semana: {week_start} — {week_end}")

team_strength = get_team_strength()
print(f"  ✅ {len(team_strength)} equipos cargados")

pitcher_info = get_pitcher_opponents(week_start, week_end, team_strength)
print(f"  ✅ {len(pitcher_info)} pitchers probables esta semana")

pit_stats = get_pitcher_stats()
tomados = get_jugadores_tomados()
roster = pd.read_csv('data/roster.csv')
roster_names = set(roster['Name'].tolist())

# Universo completo — todos los pitchers con start esta semana
todos_pitchers = list(pitcher_info.keys())
print(f"  ✅ {len(todos_pitchers)} pitchers en el universo esta semana")

# Construir tabla completa
resultados = [build_row(nombre, pitcher_info, pit_stats, tomados, roster_names)
              for nombre in todos_pitchers]
df_all = pd.DataFrame(resultados).sort_values(
    ['Starts', 'Favorabilidad'], ascending=[False, False]
)

# Separar para compatibilidad con dashboard
df_waivers = df_all[df_all['Ubicacion'] == '🔓 Waiver'].copy()
df_waivers['Breakout_Score'] = df_waivers['Favorabilidad']

# Roster
roster_resultados = []
for _, row in roster.iterrows():
    nombre = row['Name']
    info = pitcher_info.get(nombre, {})
    starts = info.get('total_starts', 0)
    oponentes = info.get('starts', [])
    fav = round(sum([s['favorabilidad'] for s in oponentes]) / len(oponentes), 1) if oponentes else 50.0
    opp_str = ' | '.join([
        f"{s['fecha']} vs {s['oponente']} ({s['dificultad']}) wOBA:{s['woba_opp']:.3f}"
        for s in oponentes
    ])
    roster_resultados.append({
        'Name': nombre,
        'Pos': row.get('Pos', ''),
        'Starts': starts,
        'Doble_Start': '⭐ DOBLE' if starts >= 2 else '➡️ Simple' if starts == 1 else '❌ Sin start',
        'Favorabilidad': fav,
        'Oponentes': opp_str if opp_str else 'Sin start / No pitcher'
    })
df_roster = pd.DataFrame(roster_resultados)

# Guardar
df_waivers.to_csv('data/schedule_waivers_sp.csv', index=False)
df_roster.to_csv('data/schedule_roster.csv', index=False)
df_all.to_csv('data/schedule_universo.csv', index=False)

# ================================
# PRINT
# ================================
print("\n" + "=" * 75)
print("⭐ SP DOBLE START — UNIVERSO COMPLETO")
print("=" * 75)
dobles = df_all[df_all['Starts'] >= 2]
for _, r in dobles.head(15).iterrows():
    print(f"  {r['Ubicacion']} {r['Name']}: ERA {r['ERA']:.2f} xERA {r['xERA']:.2f} Fav:{r['Favorabilidad']}")
    print(f"    {r['Oponentes']}")

print("\n" + "=" * 75)
print("➡️  SP SIMPLE START — Top 15 más favorables")
print("=" * 75)
simples = df_all[df_all['Starts'] == 1].head(15)
for _, r in simples.iterrows():
    print(f"  {r['Ubicacion']} {r['Name']}: ERA {r['ERA']:.2f} xERA {r['xERA']:.2f} Fav:{r['Favorabilidad']}")
    print(f"    {r['Oponentes']}")

print("\n" + "=" * 75)
print("📋 MIS PITCHERS ESTA SEMANA")
print("=" * 75)
mis_pit = df_roster[df_roster['Pos'].isin(['SP', 'RP', 'P', 'IL'])]
for _, r in mis_pit.iterrows():
    print(f"  {r['Name']} ({r['Pos']}): {r['Doble_Start']} Fav:{r['Favorabilidad']}")
    print(f"    {r['Oponentes']}")

print(f"\n✅ Guardado en data/")