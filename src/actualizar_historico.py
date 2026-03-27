import requests
import pandas as pd
from io import StringIO
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season

SEASON = get_season()
headers = {'User-Agent': 'Mozilla/5.0'}

def descargar_bat(year):
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=batter&filter=&min=1"
        "&selections=pa,ab,hit,home_run,r_total_stolen_base,walk,strikeout,"
        "batting_avg,on_base_percent,slg_percent,on_base_plus_slg,isolated_power,babip,"
        "xba,xslg,woba,xwoba,exit_velocity_avg,launch_angle_avg,barrel_batted_rate,"
        "r_run,b_rbi&chart=false&csv=true"
    )
    r = requests.get(url, headers=headers)
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    return df

def descargar_pit(year):
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=pitcher&filter=&min=1"
        "&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,"
        "p_walk,hit,p_era,p_save,xera,xba,xslg,xwoba,"
        "exit_velocity_avg,barrel_batted_rate&chart=false&csv=true"
    )
    r = requests.get(url, headers=headers)
    df = pd.read_csv(StringIO(r.text))
    df['year'] = year
    if len(df) > 0:
        df['p_whip'] = ((df['p_walk'] + df['hit']) / df['p_formatted_ip']).round(3)
    return df

# ================================
# AÑOS A ACTUALIZAR
# Temporada actual + últimas 2 completas por si hay correcciones
# ================================
# 3 últimas temporadas completas + actual en progreso
years_to_update = [SEASON - 3, SEASON - 2, SEASON - 1, SEASON]

print(f"Actualizando histórico para años: {years_to_update}")

bat_hist = pd.read_csv('data/bateo_historico.csv')
pit_hist = pd.read_csv('data/pitcheo_historico.csv')

for year in years_to_update:
    print(f"\n  Descargando {year}...")

    bat_new = descargar_bat(year)
    pit_new = descargar_pit(year)

    print(f"    Bateadores {year}: {len(bat_new)}")
    print(f"    Pitchers {year}: {len(pit_new)}")

    if len(bat_new) > 0:
        bat_hist = bat_hist[bat_hist['year'] != year]
        bat_hist = pd.concat([bat_hist, bat_new], ignore_index=True)

    if len(pit_new) > 0:
        pit_hist = pit_hist[pit_hist['year'] != year]
        pit_hist = pd.concat([pit_hist, pit_new], ignore_index=True)

bat_hist.to_csv('data/bateo_historico.csv', index=False)
pit_hist.to_csv('data/pitcheo_historico.csv', index=False)

print(f"\n✅ Histórico actualizado:")
print(f"   Bateadores: {len(bat_hist)} registros — años: {sorted(bat_hist['year'].unique())}")
print(f"   Pitchers: {len(pit_hist)} registros — años: {sorted(pit_hist['year'].unique())}")