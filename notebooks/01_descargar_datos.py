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
        f"&selections=pa,ab,hit,home_run,r_total_stolen_base,walk,strikeout,"
        f"batting_avg,on_base_percent,slg_percent,on_base_plus_slg,"
        f"isolated_power,babip,xba,xslg,woba,xwoba,"
        f"exit_velocity_avg,launch_angle_avg,barrel_batted_rate,"
        f"r_run,b_rbi"
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
        f"p_walk,hit,p_era,p_save,xera,xba,xslg,xwoba,"
        f"exit_velocity_avg,barrel_batted_rate"
        f"&chart=false&csv=true"
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    all_pitcheo.append(df)

bateo = pd.concat(all_bateo, ignore_index=True)
pitcheo = pd.concat(all_pitcheo, ignore_index=True)

print("\nVerificando columnas clave...")
print(f"r_total_stolen_base no nulos: {bateo['r_total_stolen_base'].notna().sum()}")
print(f"on_base_percent no nulos: {bateo['on_base_percent'].notna().sum()}")
print(f"r_run no nulos: {bateo['r_run'].notna().sum()}")
print(f"b_rbi no nulos: {bateo['b_rbi'].notna().sum()}")
print(f"hit (pitchers) no nulos: {pitcheo['hit'].notna().sum()}")

# Calcular WHIP = (Walks + Hits) / IP
pitcheo['p_formatted_ip'] = pd.to_numeric(pitcheo['p_formatted_ip'], errors='coerce')
pitcheo['p_whip'] = ((pitcheo['p_walk'] + pitcheo['hit']) / pitcheo['p_formatted_ip']).round(3)
print(f"p_whip calculado no nulos: {pitcheo['p_whip'].notna().sum()}")

bateo.to_csv('data/bateo_historico.csv', index=False)
pitcheo.to_csv('data/pitcheo_historico.csv', index=False)

print(f"\n✅ Bateadores: {len(bateo)} registros")
print(f"✅ Pitchers: {len(pitcheo)} registros")
print("\n--- TOP 5 HR 2025 ---")
bateo_2025 = bateo[bateo['year'] == 2025]
print(bateo_2025.sort_values('home_run', ascending=False)[['last_name, first_name', 'home_run', 'r_total_stolen_base', 'on_base_percent', 'r_run', 'b_rbi']].head())

print("\nDescargando estadísticas avanzadas adicionales...")
headers = {'User-Agent': 'Mozilla/5.0'}

for year in [2022, 2023, 2024, 2025]:
    print(f"  Bateo avanzado {year}...")
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=batter&filter=&min=10"
        f"&selections=player_age,ab,pa,hit,single,double,triple,home_run,walk,"
        f"bb_percent,batting_avg,slg_percent,on_base_percent,on_base_plus_slg,"
        f"isolated_power,babip,b_rbi,b_total_bases,r_total_stolen_base,"
        f"b_ab_scoring,b_game,b_intent_walk,r_stolen_base_pct,"
        f"xba,xslg,woba,xwoba,xobp,xiso,xbadiff,xslgdiff,"
        f"avg_swing_speed,fast_swing_rate,blasts_contact,blasts_swing,"
        f"squared_up_contact,squared_up_swing,avg_swing_length,swords,"
        f"attack_angle,attack_direction,ideal_angle_rate,vertical_swing_path,"
        f"exit_velocity_avg,launch_angle_avg,sweet_spot_percent,"
        f"barrel_batted_rate,solidcontact_percent,hard_hit_percent"
        f"&chart=false&csv=true"
    )
    r = requests.get(url, headers=headers)
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    df.to_csv(f'data/bateo_avanzado_{year}.csv', index=False)
    print(f"    ✅ {len(df)} bateadores")

for year in [2022, 2023, 2024, 2025]:
    print(f"  Pitcheo avanzado {year}...")
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=pitcher&filter=&min=5"
        f"&selections=k_percent,bb_percent,p_out,p_win,p_shutout,p_era,"
        f"p_opp_batting_avg,p_total_strike,z_swing_miss_percent,"
        f"oz_swing_miss_percent,pitch_count_fastball,pitch_count_breaking,"
        f"in_zone_percent,whiff_percent,f_strike_percent,"
        f"ff_avg_speed,ff_avg_spin,n_sl_formatted,sl_avg_speed,sl_avg_spin,"
        f"ch_avg_speed,ch_avg_spin,cu_avg_speed,cu_avg_spin,"
        f"si_avg_speed,si_avg_spin,fc_avg_speed,fc_avg_spin,"
        f"fs_avg_speed,fs_avg_spin,st_avg_speed,st_avg_spin,"
        f"fastball_avg_speed,fastball_avg_spin"
        f"&chart=false&csv=true"
    )
    r = requests.get(url, headers=headers)
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    df.to_csv(f'data/pitcheo_avanzado_{year}.csv', index=False)
    print(f"    ✅ {len(df)} pitchers")

print("\n✅ Datos avanzados descargados")