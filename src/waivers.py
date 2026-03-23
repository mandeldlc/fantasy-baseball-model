import requests
import pandas as pd
from io import StringIO
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# ================================
# OBTENER JUGADORES TOMADOS EN LA LIGA
# ================================
def get_jugadores_tomados():
    print("Conectando a Yahoo para ver jugadores tomados...")
    query = YahooFantasySportsQuery(
        league_id="31891",
        game_code="mlb",
        game_id=469,
        yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
        yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
        yahoo_access_token_json=None,
        env_file_location=Path("."),
        save_token_data_to_env_file=True
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

# ================================
# NORMALIZAR NOMBRES
# ================================
def normalizar_nombre(nombre):
    if not isinstance(nombre, str):
        return ""
    import unicodedata
    import re
    nombre = re.sub(r'\(.*?\)', '', nombre).strip()
    nombre = unicodedata.normalize('NFD', nombre)
    nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
    nombre = nombre.lower().strip()
    nombre = nombre.replace('.', '').replace('-', ' ').replace("'", '')
    return nombre

# ================================
# DESCARGAR DATOS MLB 2025
# ================================
print("Descargando todos los jugadores MLB 2025...")
headers = {'User-Agent': 'Mozilla/5.0'}

url_bat = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    "?year=2025&type=batter&filter=&min=50"
    "&selections=pa,ab,hit,home_run,r_total_stolen_base,walk,strikeout,"
    "batting_avg,on_base_percent,slg_percent,on_base_plus_slg,isolated_power,babip,"
    "xba,xslg,woba,xwoba,exit_velocity_avg,launch_angle_avg,barrel_batted_rate,"
    "r_run,b_rbi"
    "&chart=false&csv=true"
)
r = requests.get(url_bat, headers=headers)
todos_bateo = pd.read_csv(StringIO(r.text))

url_pit = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    "?year=2025&type=pitcher&filter=&min=20"
    "&selections=p_game,p_formatted_ip,p_win,p_loss,p_strikeout,"
    "p_walk,hit,p_era,p_save,xera,xba,xslg,xwoba,"
    "exit_velocity_avg,barrel_batted_rate"
    "&chart=false&csv=true"
)
r = requests.get(url_pit, headers=headers)
todos_pitcheo = pd.read_csv(StringIO(r.text))

# Arreglar nombres
todos_bateo[['last_name', 'first_name']] = todos_bateo['last_name, first_name'].str.split(', ', expand=True)
todos_bateo['Name'] = todos_bateo['first_name'] + ' ' + todos_bateo['last_name']
todos_bateo['Name_norm'] = todos_bateo['Name'].apply(normalizar_nombre)

todos_pitcheo[['last_name', 'first_name']] = todos_pitcheo['last_name, first_name'].str.split(', ', expand=True)
todos_pitcheo['Name'] = todos_pitcheo['first_name'] + ' ' + todos_pitcheo['last_name']
todos_pitcheo['Name_norm'] = todos_pitcheo['Name'].apply(normalizar_nombre)

print(f"✅ Total bateadores: {len(todos_bateo)}")
print(f"✅ Total pitchers: {len(todos_pitcheo)}")

# ================================
# FILTRAR JUGADORES TOMADOS
# ================================
jugadores_tomados = get_jugadores_tomados()
tomados_norm = [normalizar_nombre(n) for n in jugadores_tomados]
pd.DataFrame({'yahoo_name': jugadores_tomados, 'yahoo_norm': tomados_norm}).to_csv('data/jugadores_tomados.csv', index=False)

libres_bateo = todos_bateo[~todos_bateo['Name_norm'].isin(tomados_norm)].copy()
libres_pitcheo = todos_pitcheo[~todos_pitcheo['Name_norm'].isin(tomados_norm)].copy()

print(f"\nJugadores realmente libres en tu liga:")
print(f"  Bateadores: {len(libres_bateo)}")
print(f"  Pitchers: {len(libres_pitcheo)}")

# Verificar Ohtani
ohtani_check = libres_bateo[libres_bateo['Name'].str.contains('Ohtani', case=False)]
if len(ohtani_check) > 0:
    print(f"\n⚠️  Ohtani sigue apareciendo")
else:
    print("\n✅ Ohtani correctamente excluido")

# ================================
# FILTRAR ACTIVOS EN GRANDES LIGAS
# ================================
print("\nFiltrando jugadores activos...")

# Bateadores activos: PA >= 30, average real, exit velocity válida
libres_bateo = libres_bateo[
    (libres_bateo['pa'] >= 30) &
    (libres_bateo['batting_avg'] > 0) &
    (libres_bateo['exit_velocity_avg'] > 80)
].copy()

# Pitchers activos: ERA <= 15, al menos 1 juego
libres_pitcheo = libres_pitcheo[
    (libres_pitcheo['p_era'] <= 15) &
    (libres_pitcheo['p_game'] >= 1)
].copy()

print(f"  Bateadores activos libres: {len(libres_bateo)}")
print(f"  Pitchers activos libres: {len(libres_pitcheo)}")

# ================================
# SCORE BREAKOUT BATEADORES
# ================================
libres_bateo['diff_xwoba'] = libres_bateo['xwoba'] - libres_bateo['woba']
libres_bateo['breakout_score'] = 0
libres_bateo['breakout_score'] += libres_bateo['diff_xwoba'] * 100
libres_bateo['breakout_score'] += libres_bateo['barrel_batted_rate'] * 2
libres_bateo['breakout_score'] += (libres_bateo['exit_velocity_avg'] - 88) * 2
libres_bateo['diff_babip'] = 0.300 - libres_bateo['babip']
libres_bateo['breakout_score'] += libres_bateo['diff_babip'] * 50
libres_bateo['breakout_score'] += libres_bateo['woba'] * 20

# ================================
# SCORE BREAKOUT PITCHERS
# ================================
# Calcular WHIP
todos_pitcheo['p_whip'] = ((todos_pitcheo['p_walk'] + todos_pitcheo['hit']) / todos_pitcheo['p_formatted_ip']).round(3)
libres_pitcheo['diff_xera'] = libres_pitcheo['p_era'] - libres_pitcheo['xera']
libres_pitcheo['breakout_score'] = 0
libres_pitcheo['breakout_score'] += libres_pitcheo['diff_xera'] * 15
libres_pitcheo['breakout_score'] += (0.320 - libres_pitcheo['xwoba']) * 100
libres_pitcheo['breakout_score'] += (92 - libres_pitcheo['exit_velocity_avg']) * 2
libres_pitcheo['breakout_score'] += libres_pitcheo['p_strikeout'] * 0.05

# ================================
# SEPARAR SP Y RP
# ================================
libres_pitcheo['pitcher_type'] = 'SP'
libres_pitcheo.loc[
    (libres_pitcheo['p_formatted_ip'] < 50) |
    (libres_pitcheo['p_save'] > 0),
    'pitcher_type'
] = 'RP'

sp_libres = libres_pitcheo[libres_pitcheo['pitcher_type'] == 'SP'].sort_values('breakout_score', ascending=False)
rp_libres = libres_pitcheo[libres_pitcheo['pitcher_type'] == 'RP'].sort_values('breakout_score', ascending=False)

print(f"\nSP libres: {len(sp_libres)}")
print(f"RP libres: {len(rp_libres)}")

# ================================
# MOSTRAR RESULTADOS
# ================================
print("\n" + "=" * 70)
print("BATEADORES ACTIVOS EN AGENCIA LIBRE")
print("=" * 70)
print(f"{'Jugador':<22} {'PA':>4} {'HR':>4} {'wOBA':>6} {'xwOBA':>6} {'xBA':>6} {'EV':>6} {'BABIP':>6} {'Score':>7}")
print("-" * 70)
for _, r in libres_bateo.sort_values('breakout_score', ascending=False).iterrows():
    diff = r['diff_xwoba']
    arrow = "📈" if diff > 0.020 else "➡️ "
    print(f"{arrow} {r['Name']:<20} {r['pa']:>4.0f} {r['home_run']:>4.0f} "
          f"{r['woba']:>6.3f} {r['xwoba']:>6.3f} {r['xba']:>6.3f} "
          f"{r['exit_velocity_avg']:>6.1f} {r['babip']:>6.3f} {r['breakout_score']:>7.1f}")

print("\n" + "=" * 70)
print("SP ACTIVOS EN AGENCIA LIBRE")
print("=" * 70)
for _, r in sp_libres.iterrows():
    arrow = "📈" if r['diff_xera'] > 0.30 else "➡️ "
    print(f"{arrow} {r['Name']:<20} ERA:{r['p_era']:>5.2f} xERA:{r['xera']:>6.2f} "
          f"Ks:{r['p_strikeout']:>4.0f} Score:{r['breakout_score']:>7.1f}")

print("\n" + "=" * 70)
print("RP ACTIVOS EN AGENCIA LIBRE")
print("=" * 70)
for _, r in rp_libres.iterrows():
    arrow = "📈" if r['diff_xera'] > 0.30 else "➡️ "
    print(f"{arrow} {r['Name']:<20} ERA:{r['p_era']:>5.2f} xERA:{r['xera']:>6.2f} "
          f"SV:{r['p_save']:>3.0f} Ks:{r['p_strikeout']:>4.0f} Score:{r['breakout_score']:>7.1f}")

# ================================
# GUARDAR
# ================================
libres_bateo.sort_values('breakout_score', ascending=False).to_csv('data/waivers_bateadores.csv', index=False)
sp_libres.to_csv('data/waivers_sp.csv', index=False)
rp_libres.to_csv('data/waivers_rp.csv', index=False)
libres_pitcheo.sort_values('breakout_score', ascending=False).to_csv('data/waivers_pitchers.csv', index=False)
print("\n✅ Guardado en data/")