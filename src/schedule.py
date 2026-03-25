import requests
import pandas as pd
from datetime import date, timedelta
import json

def get_week_dates():
    try:
        with open('data/matchup_semana.json') as f:
            matchup = json.load(f)
        return matchup['week_start'], matchup['week_end']
    except:
        hoy = date.today()
        return str(hoy), str(hoy + timedelta(days=6))

def get_team_strength():
    """Cargar offense score de Baseball Savant por equipo"""
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

def get_pitcher_opponents(start_date, end_date, team_strength):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&gameType=R&hydrate=probablePitcher"
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
                            'xwoba_opp': opp_data.get('xwoba', 0.310)
                        })
                        pitcher_info[nombre]['total_starts'] += 1

    return pitcher_info

def build_row_waiver(row, pitcher_info):
    nombre = row['Name']
    info = pitcher_info.get(nombre, {})
    starts = info.get('total_starts', 0)
    oponentes = info.get('starts', [])
    fav_promedio = round(sum([s['favorabilidad'] for s in oponentes]) / len(oponentes), 1) if oponentes else 50.0
    opp_str = ' | '.join([f"{s['fecha']} vs {s['oponente']} ({s['dificultad']}) wOBA:{s['woba_opp']:.3f}" for s in oponentes])
    return {
        'Name': nombre,
        'Starts': starts,
        'Doble_Start': '⭐ DOBLE' if starts >= 2 else '➡️ Simple' if starts == 1 else '❌ Sin start',
        'Favorabilidad': fav_promedio,
        'Oponentes': opp_str if opp_str else 'Sin start asignado',
        'ERA': row.get('p_era', 0),
        'xERA': row.get('xera', 0),
        'Breakout_Score': row.get('breakout_score', 0)
    }

def build_row_roster(row, pitcher_info):
    nombre = row['Name']
    info = pitcher_info.get(nombre, {})
    starts = info.get('total_starts', 0)
    oponentes = info.get('starts', [])
    fav_promedio = round(sum([s['favorabilidad'] for s in oponentes]) / len(oponentes), 1) if oponentes else 50.0
    opp_str = ' | '.join([f"{s['fecha']} vs {s['oponente']} ({s['dificultad']}) wOBA:{s['woba_opp']:.3f}" for s in oponentes])
    return {
        'Name': nombre,
        'Pos': row.get('Pos', ''),
        'Starts': starts,
        'Doble_Start': '⭐ DOBLE' if starts >= 2 else '➡️ Simple' if starts == 1 else '❌ Sin start',
        'Favorabilidad': fav_promedio,
        'Oponentes': opp_str if opp_str else 'Sin start / No pitcher'
    }

# ================================
# MAIN
# ================================
print("Analizando schedule de la semana...")

week_start, week_end = get_week_dates()
print(f"Semana: {week_start} — {week_end}")

print("Cargando offense scores por equipo...")
team_strength = get_team_strength()
if team_strength:
    print(f"  ✅ {len(team_strength)} equipos cargados")
else:
    print("  ⚠️ Sin datos de equipo — usando valores por defecto")

pitcher_info = get_pitcher_opponents(week_start, week_end, team_strength)
print(f"  ✅ {len(pitcher_info)} pitchers con start asignado")

waivers_sp = pd.read_csv('data/waivers_sp.csv')
roster = pd.read_csv('data/roster.csv')

# Waivers SP
resultados = [build_row_waiver(row, pitcher_info) for _, row in waivers_sp.iterrows()]
df_waivers = pd.DataFrame(resultados).sort_values(
    ['Starts', 'Favorabilidad', 'Breakout_Score'],
    ascending=[False, False, False]
)

# Roster
roster_resultados = [build_row_roster(row, pitcher_info) for _, row in roster.iterrows()]
df_roster = pd.DataFrame(roster_resultados)

df_waivers.to_csv('data/schedule_waivers_sp.csv', index=False)
df_roster.to_csv('data/schedule_roster.csv', index=False)

# ================================
# PRINT RESULTADOS
# ================================
print("\n" + "=" * 75)
print("⭐ SP DOBLE START EN WAIVERS")
print("=" * 75)
dobles = df_waivers[df_waivers['Starts'] >= 2]
if len(dobles) > 0:
    for _, r in dobles.head(10).iterrows():
        print(f"  {r['Name']}: ERA {r['ERA']:.2f} xERA {r['xERA']:.2f} Fav:{r['Favorabilidad']}")
        print(f"    {r['Oponentes']}")
else:
    print("  Ninguno aún — pitchers probables no anunciados")

print("\n" + "=" * 75)
print("➡️  SP SIMPLE START EN WAIVERS — Top 10 más favorables")
print("=" * 75)
simples = df_waivers[df_waivers['Starts'] == 1].head(10)
for _, r in simples.iterrows():
    print(f"  {r['Name']}: ERA {r['ERA']:.2f} xERA {r['xERA']:.2f} Fav:{r['Favorabilidad']}")
    print(f"    {r['Oponentes']}")

print("\n" + "=" * 75)
print("📋 MIS PITCHERS ESTA SEMANA")
print("=" * 75)
mis_pit = df_roster[df_roster['Pos'].isin(['SP', 'RP', 'P'])]
for _, r in mis_pit.iterrows():
    print(f"  {r['Name']} ({r['Pos']}): {r['Doble_Start']} Fav:{r['Favorabilidad']}")
    print(f"    {r['Oponentes']}")

print(f"\n✅ Guardado en data/schedule_waivers_sp.csv y data/schedule_roster.csv")