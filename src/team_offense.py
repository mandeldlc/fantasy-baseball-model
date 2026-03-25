import requests
from bs4 import BeautifulSoup
import pandas as pd

TEAM_IDS = {
    109: 'Arizona Diamondbacks',
    133: 'Athletics',
    144: 'Atlanta Braves',
    110: 'Baltimore Orioles',
    111: 'Boston Red Sox',
    112: 'Chicago Cubs',
    145: 'Chicago White Sox',
    113: 'Cincinnati Reds',
    114: 'Cleveland Guardians',
    115: 'Colorado Rockies',
    116: 'Detroit Tigers',
    117: 'Houston Astros',
    118: 'Kansas City Royals',
    108: 'Los Angeles Angels',
    119: 'Los Angeles Dodgers',
    146: 'Miami Marlins',
    158: 'Milwaukee Brewers',
    142: 'Minnesota Twins',
    121: 'New York Mets',
    147: 'New York Yankees',
    143: 'Philadelphia Phillies',
    134: 'Pittsburgh Pirates',
    135: 'San Diego Padres',
    137: 'San Francisco Giants',
    136: 'Seattle Mariners',
    138: 'St. Louis Cardinals',
    139: 'Tampa Bay Rays',
    140: 'Texas Rangers',
    141: 'Toronto Blue Jays',
    120: 'Washington Nationals'
}

def scrape_team_offense(year):
    print(f"  Scraping {year}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(f'https://baseballsavant.mlb.com/league?season={year}')
    soup = BeautifulSoup(r.text, 'html.parser')
    tablas = soup.find_all('table')
    tabla = tablas[0]
    filas = tabla.find_all('tr')

    resultados = []
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        if len(celdas) < 25:
            continue

        # Obtener team_id del href
        try:
            href = celdas[0].find('a')['href']
            team_id = int(href.split('/team/')[1])
            team_name = TEAM_IDS.get(team_id, f'Team {team_id}')
        except:
            continue

        def get_val(celda):
            txt = celda.get_text(strip=True).replace(',', '').replace('%', '')
            try:
                return float(txt)
            except:
                return None

        resultados.append({
            'year': year,
            'team_id': team_id,
            'team_name': team_name,
            'pa': get_val(celdas[2]),
            'ab': get_val(celdas[3]),
            'h': get_val(celdas[4]),
            'hr': get_val(celdas[7]),
            'bb': get_val(celdas[8]),
            'so': get_val(celdas[9]),
            'avg': get_val(celdas[10]),
            'obp': get_val(celdas[11]),
            'slg': get_val(celdas[12]),
            'woba': get_val(celdas[13]),
            'barrel_rate': get_val(celdas[18]),
            'hard_hit': get_val(celdas[19]),
            'exit_velocity': get_val(celdas[20]),
            'xba': get_val(celdas[22]),
            'xslg': get_val(celdas[23]),
            'xwoba': get_val(celdas[24]),
        })

    return resultados

# ================================
# MAIN
# ================================
print("Descargando stats ofensivos Statcast por equipo 2022-2025...")

all_data = []
for year in [2022, 2023, 2024, 2025]:
    try:
        data = scrape_team_offense(year)
        all_data.extend(data)
        print(f"    ✅ {len(data)} equipos")
    except Exception as e:
        print(f"    ❌ Error {year}: {e}")

df = pd.DataFrame(all_data)

# Calcular offense score con categorías del fantasy
df['offense_score'] = (
    df['woba'].fillna(0) * 30 +
    df['xwoba'].fillna(0) * 20 +
    df['exit_velocity'].fillna(0) * 0.5 +
    df['barrel_rate'].fillna(0) * 2 +
    df['hard_hit'].fillna(0) * 0.5 +
    df['hr'].fillna(0) * 0.1 +
    df['obp'].fillna(0) * 20 +
    df['slg'].fillna(0) * 10
).round(2)

# Normalizar por año
df['offense_score_norm'] = 50.0
for year in df['year'].unique():
    mask = df['year'] == year
    mn = df.loc[mask, 'offense_score'].min()
    mx = df.loc[mask, 'offense_score'].max()
    if mx > mn:
        df.loc[mask, 'offense_score_norm'] = ((df.loc[mask, 'offense_score'] - mn) / (mx - mn) * 100).round(1)

df['dificultad'] = df['offense_score_norm'].apply(
    lambda x: '🔴 Difícil' if x > 65 else '🟢 Fácil' if x < 35 else '🟡 Normal'
)

df.to_csv('data/team_offense.csv', index=False)

# Mostrar ranking 2025
print("\n" + "=" * 75)
print("RANKING OFENSIVO STATCAST 2025 — Más peligrosos para pitchers")
print("=" * 75)
df_2025 = df[df['year'] == 2025].sort_values('offense_score_norm', ascending=False)
print(f"{'Equipo':<30} {'wOBA':>6} {'xwOBA':>6} {'EV':>5} {'Barrel%':>7} {'Score':>7} {'Dific':>10}")
print("-" * 75)
for _, r in df_2025.iterrows():
    print(f"{r['team_name']:<30} {r['woba']:>6.3f} {r['xwoba']:>6.3f} {r['exit_velocity']:>5.1f} {r['barrel_rate']:>7.1f} {r['offense_score_norm']:>7.1f} {r['dificultad']:>10}")

print(f"\n✅ {len(df)} registros guardados en data/team_offense.csv")