import requests
import pandas as pd
from io import StringIO

print("Descargando datos de Baseball Savant...")

years = [2022, 2023, 2024, 2025]
all_bateo = []
all_pitcheo = []

for year in years:
    print(f"  Bateo {year}...")
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=batter&filter=&min=10"
        f"&selections=pa,ab,hit,home_run,stolen_base,walk,strikeout,"
        f"batting_avg,on_base_pct,slg_pct,on_base_plus_slg,"
        f"isolated_power,babip,xba,xslg,woba,xwoba,"
        f"exit_velocity_avg,launch_angle_avg,barrel_batted_rate"
        f"&chart=false&csv=true"
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    all_bateo.append(df)

for year in years:
    print(f"  Pitcheo {year}...")
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=pitcher&filter=&min=5"
        f"&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,"
        f"p_walk,p_era,whip,p_save,xera,xba,xslg,xwoba,"
        f"exit_velocity_avg,barrel_batted_rate"
        f"&chart=false&csv=true"
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    all_pitcheo.append(df)

bateo = pd.concat(all_bateo, ignore_index=True)
pitcheo = pd.concat(all_pitcheo, ignore_index=True)

# Verificar que las columnas tienen datos
print("\nVerificando columnas clave...")
print(f"stolen_base no nulos: {bateo['stolen_base'].notna().sum()}")
print(f"on_base_pct no nulos: {bateo['on_base_pct'].notna().sum()}")
print(f"whip no nulos: {pitcheo['whip'].notna().sum()}")

bateo.to_csv('data/bateo_historico.csv', index=False)
pitcheo.to_csv('data/pitcheo_historico.csv', index=False)

print(f"\n✅ Bateadores: {len(bateo)} registros")
print(f"✅ Pitchers: {len(pitcheo)} registros")
print("\n--- TOP 5 HR 2025 ---")
bateo_2025 = bateo[bateo['year'] == 2025]
print(bateo_2025.sort_values('home_run', ascending=False)[['last_name, first_name', 'home_run', 'stolen_base', 'on_base_pct']].head())