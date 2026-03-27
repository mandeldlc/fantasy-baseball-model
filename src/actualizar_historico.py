import requests
import pandas as pd
from io import StringIO
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season

SEASON = get_season()
headers = {'User-Agent': 'Mozilla/5.0'}

print(f"Descargando data {SEASON} para histórico...")

# Bateadores 2026
url_bat = (
    f"https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={SEASON}&type=batter&filter=&min=1"
    "&selections=pa,ab,hit,home_run,r_total_stolen_base,walk,strikeout,"
    "batting_avg,on_base_percent,slg_percent,on_base_plus_slg,isolated_power,babip,"
    "xba,xslg,woba,xwoba,exit_velocity_avg,launch_angle_avg,barrel_batted_rate,"
    "r_run,b_rbi&chart=false&csv=true"
)
r = requests.get(url_bat, headers=headers)
bat_new = pd.read_csv(StringIO(r.text))
bat_new['year'] = SEASON
print(f"  Bateadores {SEASON}: {len(bat_new)}")

# Pitchers 2026
url_pit = (
    f"https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={SEASON}&type=pitcher&filter=&min=1"
    "&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,"
    "p_walk,hit,p_era,p_save,xera,xba,xslg,xwoba,"
    "exit_velocity_avg,barrel_batted_rate&chart=false&csv=true"
)
r = requests.get(url_pit, headers=headers)
pit_new = pd.read_csv(StringIO(r.text))
pit_new['year'] = SEASON
print(f"  Pitchers {SEASON}: {len(pit_new)}")

if len(bat_new) > 0:
    # Cargar histórico
    bat_hist = pd.read_csv('data/bateo_historico.csv')
    # Eliminar datos 2026 anteriores si existen
    bat_hist = bat_hist[bat_hist['year'] != SEASON]
    # Calcular WHIP para pitchers
    bat_hist = pd.concat([bat_hist, bat_new], ignore_index=True)
    bat_hist.to_csv('data/bateo_historico.csv', index=False)
    print(f"  ✅ bateo_historico.csv actualizado: {len(bat_hist)} registros")

if len(pit_new) > 0:
    pit_hist = pd.read_csv('data/pitcheo_historico.csv')
    pit_hist = pit_hist[pit_hist['year'] != SEASON]
    # Calcular WHIP
    pit_new['p_whip'] = ((pit_new['p_walk'] + pit_new['hit']) / pit_new['p_formatted_ip']).round(3)
    pit_hist = pd.concat([pit_hist, pit_new], ignore_index=True)
    pit_hist.to_csv('data/pitcheo_historico.csv', index=False)
    print(f"  ✅ pitcheo_historico.csv actualizado: {len(pit_hist)} registros")

print(f"\n✅ Histórico actualizado con data {SEASON}")