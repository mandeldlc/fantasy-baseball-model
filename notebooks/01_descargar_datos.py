import requests
import pandas as pd

print("Descargando datos de Baseball Savant...")

# Bateo - estadísticas avanzadas Statcast 2022-2025
years = [2022, 2023, 2024, 2025]
all_bateo = []

for year in years:
    print(f"  Bateo {year}...")
    url = f"https://baseballsavant.mlb.com/leaderboard/custom?year={year}&type=batter&filter=&min=10&selections=pa,ab,hit,home_run,stolen_base,walk,strikeout,batting_avg,on_base_pct,slg_pct,on_base_plus_slg,isolated_power,babip,xba,xslg,woba,xwoba,exit_velocity_avg,launch_angle_avg,barrel_batted_rate&chart=false&x=xba&y=xba&r=no&chartType=beeswarm&csv=true"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(pd.io.common.StringIO(r.text))
    df['Season'] = year
    all_bateo.append(df)

bateo = pd.concat(all_bateo, ignore_index=True)
bateo.to_csv('data/bateo_historico.csv', index=False)
print(f"✅ Bateadores: {len(bateo)} registros")
print(f"Columnas: {list(bateo.columns[:10])}")

# Pitcheo
all_pitcheo = []
for year in years:
    print(f"  Pitcheo {year}...")
    url = f"https://baseballsavant.mlb.com/leaderboard/custom?year={year}&type=pitcher&filter=&min=5&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,p_era,whip,p_save,xera,xba,xslg,xwoba,exit_velocity_avg,barrel_batted_rate&chart=false&csv=true"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(pd.io.common.StringIO(r.text))
    df['Season'] = year
    all_pitcheo.append(df)

pitcheo = pd.concat(all_pitcheo, ignore_index=True)
pitcheo.to_csv('data/pitcheo_historico.csv', index=False)
print(f"✅ Pitchers: {len(pitcheo)} registros")

print("\n--- TOP 5 HR ---")
print(bateo.sort_values('home_run', ascending=False)[['last_name, first_name', 'home_run', 'Season']].head())