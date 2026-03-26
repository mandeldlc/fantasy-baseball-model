import requests
import pandas as pd
from io import StringIO

headers = {'User-Agent': 'Mozilla/5.0'}

# IDs de equipos MLB
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

def get_pitcher_id(nombre):
    """Buscar player_id del pitcher en Baseball Savant"""
    pitcheo = pd.read_csv('data/pitcheo_historico.csv')
    pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
    pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']
    match = pitcheo[pitcheo['Name'] == nombre]
    if len(match) > 0:
        return match.iloc[0]['player_id']
    return None

def get_pitcher_vs_team(pitcher_id, team_id, years=[2022,2023,2024,2025]):
    """Obtener stats del pitcher vs equipo específico"""
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
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    try:
        df = pd.read_csv(StringIO(r.text))
        if len(df) == 0:
            return None
        # Calcular stats agregadas
        stats = {
            'pitcher_id': pitcher_id,
            'team_id': team_id,
            'pa': len(df[df['events'].notna()]),
            'hits': len(df[df['events'].isin(['single','double','triple','home_run'])]),
            'hr': len(df[df['events'] == 'home_run']),
            'so': len(df[df['events'] == 'strikeout']),
            'bb': len(df[df['events'] == 'walk']),
        }
        if 'estimated_woba_using_speedangle' in df.columns:
            stats['xwoba'] = round(df['estimated_woba_using_speedangle'].mean(), 3)
        if 'launch_speed' in df.columns:
            stats['ev'] = round(df['launch_speed'].dropna().mean(), 1)
        stats['avg'] = round(stats['hits'] / stats['pa'], 3) if stats['pa'] > 0 else 0
        return stats
    except:
        return None

# Test con Logan Gilbert vs Cleveland
pitcher_id = get_pitcher_id('Logan Gilbert')
team_id = TEAM_IDS.get('Cleveland Guardians')
print(f"Logan Gilbert ID: {pitcher_id}")
print(f"Cleveland ID: {team_id}")

stats = get_pitcher_vs_team(pitcher_id, team_id)
print(f"Stats históricos: {stats}")