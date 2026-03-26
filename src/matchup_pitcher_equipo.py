import requests
import pandas as pd
from io import StringIO
import json

headers = {'User-Agent': 'Mozilla/5.0'}

TEAM_IDS = {
    'Arizona Diamondbacks': 109, 'Athletics': 133, 'Atlanta Braves': 144,
    'Baltimore Orioles': 110, 'Boston Red Sox': 111, 'Chicago Cubs': 112,
    'Chicago White Sox': 145, 'Cincinnati Reds': 113, 'Cleveland Guardians': 114,
    'Colorado Rockies': 115, 'Detroit Tigers': 116, 'Houston Astros': 117,
    'Kansas City Royals': 118, 'Los Angeles Angels': 108, 'Los Angeles Dodgers': 119,
    'Miami Marlins': 146, 'Milwaukee Brewers': 158, 'Minnesota Twins': 142,
    'New York Mets': 121, 'New York Yankees': 147, 'Philadelphia Phillies': 143,
    'Pittsburgh Pirates': 134, 'San Diego Padres': 135, 'San Francisco Giants': 137,
    'Seattle Mariners': 136, 'St. Louis Cardinals': 138, 'Tampa Bay Rays': 139,
    'Texas Rangers': 140, 'Toronto Blue Jays': 141, 'Washington Nationals': 120
}

def get_pitcher_ids():
    pitcheo = pd.read_csv('data/pitcheo_historico.csv')
    pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
    pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']
    return dict(zip(pitcheo['Name'], pitcheo['player_id']))

def get_pitcher_vs_team(pitcher_id, team_id, years=[2022,2023,2024,2025]):
    years_str = '%7C'.join([str(y) for y in years])
    url = (
        f'https://baseballsavant.mlb.com/statcast_search/csv?all=true'
        f'&hfGT=R%7C&hfSea={years_str}%7C&player_type=pitcher'
        f'&pitchers_lookup%5B%5D={pitcher_id}&opponent_team={team_id}'
        f'&group_by=name&min_pitches=0&min_results=0&min_pas=0'
        f'&chk_stats_pa=on&chk_stats_hits=on&chk_stats_hr=on'
        f'&chk_stats_so=on&chk_stats_bb=on&chk_stats_avg=on'
        f'&chk_stats_slg=on&chk_stats_obp=on&chk_stats_woba=on'
        f'&chk_stats_xwoba=on&chk_stats_exit_velocity_avg=on'
        f'&type=details'
    )
    try:
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(StringIO(r.text))
        if len(df) == 0:
            return None
        pa = len(df[df['events'].notna()])
        if pa < 10:
            return None
        hits = len(df[df['events'].isin(['single','double','triple','home_run'])])
        hr = len(df[df['events'] == 'home_run'])
        so = len(df[df['events'] == 'strikeout'])
        bb = len(df[df['events'] == 'walk'])
        xwoba = round(df['estimated_woba_using_speedangle'].mean(), 3) if 'estimated_woba_using_speedangle' in df.columns else None
        ev = round(df['launch_speed'].dropna().mean(), 1) if 'launch_speed' in df.columns else None
        avg = round(hits / pa, 3) if pa > 0 else 0
        k_pct = round(so / pa * 100, 1) if pa > 0 else 0

        # Score favorabilidad — menor xwOBA y EV = más favorable para el pitcher
        fav_score = 0
        if xwoba:
            if xwoba < 0.280: fav_score += 3
            elif xwoba < 0.300: fav_score += 2
            elif xwoba < 0.320: fav_score += 1
            elif xwoba > 0.360: fav_score -= 2
            elif xwoba > 0.340: fav_score -= 1
        if ev:
            if ev < 85: fav_score += 3
            elif ev < 87: fav_score += 2
            elif ev < 89: fav_score += 1
            elif ev > 92: fav_score -= 2
            elif ev > 90: fav_score -= 1
        if k_pct > 30: fav_score += 2
        elif k_pct > 25: fav_score += 1

        clasificacion = '🟢 Favorable' if fav_score >= 3 else '🔴 Difícil' if fav_score <= -1 else '🟡 Normal'

        return {
            'pa': pa, 'hits': hits, 'hr': hr, 'so': so, 'bb': bb,
            'avg': avg, 'k_pct': k_pct,
            'xwoba': xwoba, 'ev': ev,
            'fav_score': fav_score,
            'clasificacion': clasificacion
        }
    except Exception as e:
        return None

# ================================
# MAIN — TOP 100 PITCHERS
# ================================
print("Calculando favorabilidad histórica pitcher vs equipo...")

pitcher_ids = get_pitcher_ids()

# Cargar top 50 SP + top 50 RP de waivers
sp = pd.read_csv('data/waivers_sp.csv')
rp = pd.read_csv('data/waivers_rp.csv')
roster = pd.read_csv('data/roster.csv')

top_sp = sp.nlargest(50, 'breakout_score')['Name'].tolist()
top_rp = rp.nlargest(50, 'breakout_score')['Name'].tolist()
roster_pit = roster[roster['Pos'].isin(['SP', 'RP', 'P'])]['Name'].tolist()

todos_pitchers = list(set(top_sp + top_rp + roster_pit))
print(f"Total pitchers a analizar: {len(todos_pitchers)}")

# Cargar resultados existentes para no repetir
try:
    existentes = pd.read_csv('data/favorabilidad_pitcher_equipo_full.csv')
    ya_procesados = set(zip(existentes['Name'], existentes['Oponente']))
    print(f"Ya procesados: {len(existentes)} matchups")
except:
    existentes = pd.DataFrame()
    ya_procesados = set()

resultados = existentes.to_dict('records') if len(existentes) > 0 else []

total = len(todos_pitchers) * len(TEAM_IDS)
procesados = 0

for nombre in todos_pitchers:
    pitcher_id = pitcher_ids.get(nombre)
    if not pitcher_id:
        continue

    for team_name, team_id in TEAM_IDS.items():
        if (nombre, team_name) in ya_procesados:
            procesados += 1
            continue

        procesados += 1
        if procesados % 50 == 0:
            print(f"  Progreso: {procesados}/{total} ({round(procesados/total*100,1)}%)")

        stats = get_pitcher_vs_team(pitcher_id, team_id)

        if stats:
            resultados.append({
                'Name': nombre,
                'Oponente': team_name,
                'PA_hist': stats['pa'],
                'AVG_hist': stats['avg'],
                'K%_hist': stats['k_pct'],
                'xwOBA_hist': stats['xwoba'],
                'EV_hist': stats['ev'],
                'Fav_Score': stats['fav_score'],
                'Clasificacion': stats['clasificacion']
            })
        else:
            resultados.append({
                'Name': nombre,
                'Oponente': team_name,
                'PA_hist': 0,
                'AVG_hist': None,
                'K%_hist': None,
                'xwOBA_hist': None,
                'EV_hist': None,
                'Fav_Score': 0,
                'Clasificacion': '🟡 Sin historial'
            })

        # Guardar cada 100 para no perder progreso
        if procesados % 100 == 0:
            pd.DataFrame(resultados).to_csv('data/favorabilidad_pitcher_equipo_full.csv', index=False)

df_final = pd.DataFrame(resultados)
df_final.to_csv('data/favorabilidad_pitcher_equipo_full.csv', index=False)

con_historial = df_final[df_final['PA_hist'] >= 10]
print(f"\n✅ Total matchups: {len(df_final)}")
print(f"✅ Con historial real: {len(con_historial)}")
print(f"✅ Guardado en data/favorabilidad_pitcher_equipo_full.csv")