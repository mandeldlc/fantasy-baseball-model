import requests
import pandas as pd
from io import StringIO
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_blend_weights, get_season, get_min_pa, get_min_ip

load_dotenv()

SEASON = get_season()
SEASON_PREV = SEASON - 1
W_HIST, W_CURR = get_blend_weights()
MIN_PA = get_min_pa()
MIN_IP = get_min_ip()

print(f"Temporada {SEASON} — Blend {int(W_HIST*100)}% hist / {int(W_CURR*100)}% {SEASON}")

def get_jugadores_tomados():
    print("Conectando a Yahoo para ver jugadores tomados...")
    query = YahooFantasySportsQuery(
        league_id="31891", game_code="mlb", game_id=469,
        yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
        yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
        yahoo_access_token_json=None,
        env_file_location=Path("."), save_token_data_to_env_file=True
    )
    tomados = []
    for team_id in range(1, 13):
        try:
            roster = query.get_team_roster_by_week(team_id=team_id, chosen_week=1)
            for player in roster.players:
                tomados.append(player.name.full)
        except Exception as e:
            print(f"  Error equipo {team_id}: {e}")
    print(f"✅ Jugadores tomados en la liga: {len(tomados)}")
    return tomados

def normalizar_nombre(nombre):
    if not isinstance(nombre, str):
        return ""
    import unicodedata, re
    nombre = re.sub(r'\(.*?\)', '', nombre).strip()
    nombre = unicodedata.normalize('NFD', nombre)
    nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
    return nombre.lower().strip().replace('.', '').replace('-', ' ').replace("'", '')

def split_nombre(df):
    if len(df) == 0:
        df['last_name'] = ''
        df['first_name'] = ''
        df['Name'] = ''
        df['Name_norm'] = ''
        return df
    split = df['last_name, first_name'].str.split(', ', n=1, expand=True)
    df['last_name'] = split.iloc[:, 0]
    df['first_name'] = split.iloc[:, 1] if split.shape[1] > 1 else ''
    df['Name'] = (df['first_name'] + ' ' + df['last_name']).str.strip()
    df['Name_norm'] = df['Name'].apply(normalizar_nombre)
    return df

def descargar_bateo(year, min_pa=1):
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=batter&filter=&min={min_pa}"
        "&selections=pa,ab,hit,home_run,r_total_stolen_base,walk,strikeout,"
        "batting_avg,on_base_percent,slg_percent,on_base_plus_slg,isolated_power,babip,"
        "xba,xslg,woba,xwoba,exit_velocity_avg,launch_angle_avg,barrel_batted_rate,"
        "r_run,b_rbi&chart=false&csv=true"
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(StringIO(r.text))
    df['data_year'] = year
    return split_nombre(df)

def descargar_pitcheo(year, min_ip=1):
    url = (
        f"https://baseballsavant.mlb.com/leaderboard/custom"
        f"?year={year}&type=pitcher&filter=&min={min_ip}"
        "&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,"
        "p_walk,hit,p_era,p_save,xera,xba,xslg,xwoba,"
        "exit_velocity_avg,barrel_batted_rate&chart=false&csv=true"
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    df = pd.read_csv(StringIO(r.text))
    df['data_year'] = year
    return split_nombre(df)

# ================================
# DESCARGAR Y HACER BLEND
# ================================
print(f"\nDescargando datos {SEASON}...")
bat_curr = descargar_bateo(SEASON, min_pa=1)
pit_curr = descargar_pitcheo(SEASON, min_ip=1)
print(f"  {SEASON}: {len(bat_curr)} bateadores, {len(pit_curr)} pitchers")

print(f"Descargando datos {SEASON_PREV}...")
bat_prev = descargar_bateo(SEASON_PREV, min_pa=50)
pit_prev = descargar_pitcheo(SEASON_PREV, min_ip=20)
print(f"  {SEASON_PREV}: {len(bat_prev)} bateadores, {len(pit_prev)} pitchers")

def blend_bateo(curr, prev):
    curr_names = set(curr['Name_norm']) if len(curr) > 0 else set()
    blend_rows = []
    for _, r in prev.iterrows():
        if r['Name_norm'] in curr_names:
            r_curr = curr[curr['Name_norm'] == r['Name_norm']].iloc[0]
            pa_curr = r_curr.get('pa', 0)
            # Con al menos 1 PA ya aplicamos blend proporcional
            w = min(W_CURR * (pa_curr / 50), W_CURR) if pa_curr < 50 else W_CURR
            w_h = 1 - w
            blended = r.copy()
            for col in ['woba', 'xwoba', 'babip', 'exit_velocity_avg', 'barrel_batted_rate', 'xba', 'xslg']:
                if col in r and col in r_curr and pd.notna(r[col]) and pd.notna(r_curr[col]):
                    blended[col] = round(w_h * r[col] + w * r_curr[col], 3)
            blend_rows.append(blended)
        else:
            blend_rows.append(r)
    solo_curr = curr[~curr['Name_norm'].isin(set(prev['Name_norm']))] if len(prev) > 0 else curr
    return pd.concat([pd.DataFrame(blend_rows), solo_curr], ignore_index=True)

def blend_pitcheo(curr, prev):
    curr_names = set(curr['Name_norm']) if len(curr) > 0 else set()
    blend_rows = []
    for _, r in prev.iterrows():
        if r['Name_norm'] in curr_names:
            r_curr = curr[curr['Name_norm'] == r['Name_norm']].iloc[0]
            ip_curr = r_curr.get('p_formatted_ip', 0)
            # Con al menos 1 IP ya aplicamos blend proporcional
            w = min(W_CURR * (ip_curr / 20), W_CURR) if ip_curr < 20 else W_CURR
            w_h = 1 - w
            blended = r.copy()
            for col in ['p_era', 'xera', 'xwoba', 'exit_velocity_avg', 'barrel_batted_rate']:
                if col in r and col in r_curr and pd.notna(r[col]) and pd.notna(r_curr[col]):
                    blended[col] = round(w_h * r[col] + w * r_curr[col], 3)
            blend_rows.append(blended)
        else:
            blend_rows.append(r)
    solo_curr = curr[~curr['Name_norm'].isin(set(prev['Name_norm']))] if len(prev) > 0 else curr
    return pd.concat([pd.DataFrame(blend_rows), solo_curr], ignore_index=True)

print("\nAplicando blend...")
todos_bateo = blend_bateo(bat_curr, bat_prev)
todos_pitcheo = blend_pitcheo(pit_curr, pit_prev)
print(f"  ✅ Bateadores blend: {len(todos_bateo)}")
print(f"  ✅ Pitchers blend: {len(todos_pitcheo)}")

# ================================
# FILTRAR JUGADORES TOMADOS
# ================================
jugadores_tomados = get_jugadores_tomados()
tomados_norm = [normalizar_nombre(n) for n in jugadores_tomados]
pd.DataFrame({'yahoo_name': jugadores_tomados, 'yahoo_norm': tomados_norm}).to_csv('data/jugadores_tomados.csv', index=False)

libres_bateo = todos_bateo[~todos_bateo['Name_norm'].isin(tomados_norm)].copy()
libres_pitcheo = todos_pitcheo[~todos_pitcheo['Name_norm'].isin(tomados_norm)].copy()

print(f"\nJugadores libres en la liga:")
print(f"  Bateadores: {len(libres_bateo)}")
print(f"  Pitchers: {len(libres_pitcheo)}")

# ================================
# FILTRAR ACTIVOS
# ================================
libres_bateo = libres_bateo[
    (libres_bateo['pa'] >= MIN_PA) &
    (libres_bateo['batting_avg'] > 0) &
    (libres_bateo['batting_avg'].notna()) &
    (libres_bateo['exit_velocity_avg'] > 80) &
    (libres_bateo['woba'].notna()) &
    (libres_bateo['xwoba'].notna())
].copy()

libres_pitcheo = libres_pitcheo[
    (libres_pitcheo['p_era'] <= 15) &
    (libres_pitcheo['p_era'].notna()) &
    (libres_pitcheo['p_game'] >= 1) &
    (libres_pitcheo['xera'].notna())
].copy()

print(f"\nActivos libres después de filtros:")
print(f"  Bateadores: {len(libres_bateo)}")
print(f"  Pitchers: {len(libres_pitcheo)}")

# ================================
# BREAKOUT SCORES
# ================================
libres_bateo['diff_xwoba'] = libres_bateo['xwoba'] - libres_bateo['woba']
libres_bateo['breakout_score'] = (
    libres_bateo['diff_xwoba'] * 100 +
    libres_bateo['barrel_batted_rate'] * 2 +
    (libres_bateo['exit_velocity_avg'] - 88) * 2 +
    (0.300 - libres_bateo['babip']) * 50 +
    libres_bateo['woba'] * 20
)
libres_bateo['diff_babip'] = 0.300 - libres_bateo['babip']

todos_pitcheo['p_whip'] = ((todos_pitcheo['p_walk'] + todos_pitcheo['hit']) / todos_pitcheo['p_formatted_ip']).round(3)
libres_pitcheo['diff_xera'] = libres_pitcheo['p_era'] - libres_pitcheo['xera']
libres_pitcheo['breakout_score'] = (
    libres_pitcheo['diff_xera'] * 15 +
    (0.320 - libres_pitcheo['xwoba']) * 100 +
    (92 - libres_pitcheo['exit_velocity_avg']) * 2 +
    libres_pitcheo['p_strikeout'] * 0.05
)

# ================================
# SEPARAR SP Y RP
# ================================
libres_pitcheo['pitcher_type'] = 'SP'
libres_pitcheo.loc[
    (libres_pitcheo['p_formatted_ip'] < 50) |
    (libres_pitcheo['p_save'] > 0), 'pitcher_type'
] = 'RP'

sp_libres = libres_pitcheo[libres_pitcheo['pitcher_type'] == 'SP'].sort_values('breakout_score', ascending=False)
rp_libres = libres_pitcheo[libres_pitcheo['pitcher_type'] == 'RP'].sort_values('breakout_score', ascending=False)

print(f"\nSP libres: {len(sp_libres)}")
print(f"RP libres: {len(rp_libres)}")

# ================================
# MOSTRAR TOP 20
# ================================
print("\n" + "=" * 70)
print(f"BATEADORES — {SEASON} (blend {int(W_HIST*100)}/{int(W_CURR*100)})")
print("=" * 70)
for _, r in libres_bateo.sort_values('breakout_score', ascending=False).head(20).iterrows():
    arrow = "📈" if r['diff_xwoba'] > 0.020 else "➡️ "
    print(f"{arrow} {r['Name']:<20} {r['pa']:>4.0f} {r['home_run']:>4.0f} "
          f"{r['woba']:>6.3f} {r['xwoba']:>6.3f} {r['exit_velocity_avg']:>6.1f} {r['breakout_score']:>7.1f}")

print("\n" + "=" * 70)
print(f"SP — {SEASON} (blend {int(W_HIST*100)}/{int(W_CURR*100)})")
print("=" * 70)
for _, r in sp_libres.head(20).iterrows():
    arrow = "📈" if r['diff_xera'] > 0.30 else "➡️ "
    print(f"{arrow} {r['Name']:<20} ERA:{r['p_era']:>5.2f} xERA:{r['xera']:>6.2f} Ks:{r['p_strikeout']:>4.0f} Score:{r['breakout_score']:>7.1f}")

print("\n" + "=" * 70)
print(f"RP — {SEASON} (blend {int(W_CURR*100)}/{int(W_CURR*100)})")
print("=" * 70)
for _, r in rp_libres.head(20).iterrows():
    arrow = "📈" if r['diff_xera'] > 0.30 else "➡️ "
    print(f"{arrow} {r['Name']:<20} ERA:{r['p_era']:>5.2f} xERA:{r['xera']:>6.2f} SV:{r['p_save']:>3.0f} Score:{r['breakout_score']:>7.1f}")

# ================================
# GUARDAR
# ================================
libres_bateo.sort_values('breakout_score', ascending=False).to_csv('data/waivers_bateadores.csv', index=False)
sp_libres.to_csv('data/waivers_sp.csv', index=False)
rp_libres.to_csv('data/waivers_rp.csv', index=False)
libres_pitcheo.sort_values('breakout_score', ascending=False).to_csv('data/waivers_pitchers.csv', index=False)
print("\n✅ Guardado en data/")