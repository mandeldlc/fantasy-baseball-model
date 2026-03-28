import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_blend_weights

SEASON = get_season()
W_HIST, W_CURR = get_blend_weights()

# ================================
# CARGAR ROSTER ACTUAL
# ================================
roster = pd.read_csv('data/roster.csv')
mis_bateadores_list = roster[~roster['Pos'].isin(['SP', 'RP', 'P', 'IL'])]['Name'].tolist()
mis_pitchers_list = roster[roster['Pos'].isin(['SP', 'RP', 'P', 'IL', 'BN'])]['Name'].tolist()

# ================================
# CARGAR HISTÓRICO
# ================================
bateo_hist = pd.read_csv('data/bateo_historico.csv')
bateo_hist[['last_name', 'first_name']] = bateo_hist['last_name, first_name'].str.split(', ', expand=True)
bateo_hist['Name'] = bateo_hist['first_name'] + ' ' + bateo_hist['last_name']

pitcheo_hist = pd.read_csv('data/pitcheo_historico.csv')
pitcheo_hist[['last_name', 'first_name']] = pitcheo_hist['last_name, first_name'].str.split(', ', expand=True)
pitcheo_hist['Name'] = pitcheo_hist['first_name'] + ' ' + pitcheo_hist['last_name']

# ================================
# BLEND BATEADORES
# ================================
bat_curr = bateo_hist[bateo_hist['year'] == SEASON].copy()
bat_prev = bateo_hist[bateo_hist['year'] == SEASON - 1].copy()

blend_bat_rows = []
for _, r in bat_prev.iterrows():
    curr = bat_curr[bat_curr['Name'] == r['Name']]
    if len(curr) > 0:
        r_curr = curr.iloc[0]
        pa_curr = float(r_curr.get('pa', 0)) if pd.notna(r_curr.get('pa', 0)) else 0
        w = min(W_CURR * (pa_curr / 50), W_CURR) if pa_curr < 50 else W_CURR
        w_h = 1 - w
        blended = r.copy()
        for col in ['woba', 'xwoba', 'babip', 'exit_velocity_avg', 'barrel_batted_rate', 'on_base_plus_slg', 'home_run']:
            if col in r and col in r_curr and pd.notna(r[col]) and pd.notna(r_curr[col]):
                blended[col] = round(w_h * float(r[col]) + w * float(r_curr[col]), 3)
        blend_bat_rows.append(blended)
    else:
        blend_bat_rows.append(r)

solo_bat_curr = bat_curr[~bat_curr['Name'].isin(set(bat_prev['Name']))]
bateo = pd.concat([pd.DataFrame(blend_bat_rows), solo_bat_curr], ignore_index=True)

# ================================
# BLEND PITCHEO
# ================================
pit_curr = pitcheo_hist[pitcheo_hist['year'] == SEASON].copy()
pit_prev = pitcheo_hist[pitcheo_hist['year'] == SEASON - 1].copy()

blend_pit_rows = []
for _, r in pit_prev.iterrows():
    curr = pit_curr[pit_curr['Name'] == r['Name']]
    if len(curr) > 0:
        r_curr = curr.iloc[0]
        ip_curr = float(r_curr.get('p_formatted_ip', 0)) if pd.notna(r_curr.get('p_formatted_ip', 0)) else 0
        w = min(W_CURR * (ip_curr / 20), W_CURR) if ip_curr < 20 else W_CURR
        w_h = 1 - w
        blended = r.copy()
        for col in ['p_era', 'xera', 'xwoba', 'exit_velocity_avg', 'barrel_batted_rate', 'p_strikeout']:
            if col in r and col in r_curr and pd.notna(r[col]) and pd.notna(r_curr[col]):
                blended[col] = round(w_h * float(r[col]) + w * float(r_curr[col]), 3)
        blend_pit_rows.append(blended)
    else:
        blend_pit_rows.append(r)

solo_pit_curr = pit_curr[~pit_curr['Name'].isin(set(pit_prev['Name']))]
pitcheo = pd.concat([pd.DataFrame(blend_pit_rows), solo_pit_curr], ignore_index=True)

# ================================
# FILTRAR POR POSICIÓN DEL ROSTER
# ================================
bateo = bateo[bateo['Name'].isin(mis_bateadores_list)].copy()
pitcheo = pitcheo[pitcheo['Name'].isin(mis_pitchers_list)].copy()

print(f"Blend {SEASON-1}/{SEASON} — Pesos: {int(W_HIST*100)}% hist / {int(W_CURR*100)}% actual")
print(f"Bateadores con data: {len(bateo)}")
print(f"Pitchers con data: {len(pitcheo)}")

# ================================
# SCORE BATEADORES
# ================================
def score_bateador(row):
    score = 0
    score += row['home_run'] * 0.30
    score += row['on_base_plus_slg'] * 20
    score += row['woba'] * 15
    score += row['xwoba'] * 10
    score += row['barrel_batted_rate'] * 0.5
    score += row['exit_velocity_avg'] * 0.1
    return round(score, 2)

def score_pitcher(row):
    score = 0
    score += (5 - row['p_era']) * 5
    score += (5 - row['xera']) * 3
    score += row['p_strikeout'] * 0.1
    score += row['p_win'] * 2
    score += row['p_save'] * 3
    score += (0.4 - row['xwoba']) * 20
    score -= row['exit_velocity_avg'] * 0.1
    return round(score, 2)

if len(bateo) > 0:
    bateo['score'] = bateo.apply(score_bateador, axis=1)
    if bateo['score'].max() > bateo['score'].min():
        bateo['score'] = ((bateo['score'] - bateo['score'].min()) /
                          (bateo['score'].max() - bateo['score'].min()) * 100).round(1)
    bateo = bateo.sort_values('score', ascending=False)

if len(pitcheo) > 0:
    pitcheo['score'] = pitcheo.apply(score_pitcher, axis=1)
    if pitcheo['score'].max() > pitcheo['score'].min():
        pitcheo['score'] = ((pitcheo['score'] - pitcheo['score'].min()) /
                            (pitcheo['score'].max() - pitcheo['score'].min()) * 100).round(1)
    pitcheo = pitcheo.sort_values('score', ascending=False)

# ================================
# MOSTRAR
# ================================
print("\n" + "=" * 65)
print(f"RECOMENDACIONES SEMANALES - BATEADORES (blend {SEASON-1}/{SEASON})")
print("=" * 65)
print(f"{'Jugador':<22} {'HR':>4} {'OPS':>6} {'wOBA':>6} {'xwOBA':>6} {'Score':>6}")
print("-" * 65)
for _, r in bateo.iterrows():
    emoji = "🟢" if r['score'] >= 70 else "🟡" if r['score'] >= 40 else "🔴"
    print(f"{emoji} {r['Name']:<20} {r['home_run']:>4.0f} {r['on_base_plus_slg']:>6.3f} {r['woba']:>6.3f} {r['xwoba']:>6.3f} {r['score']:>6.1f}")

print("\n" + "=" * 65)
print(f"RECOMENDACIONES SEMANALES - PITCHERS (blend {SEASON-1}/{SEASON})")
print("=" * 65)
print(f"{'Pitcher':<22} {'ERA':>5} {'xERA':>6} {'Ks':>4} {'W':>3} {'SV':>3} {'Score':>6}")
print("-" * 65)
for _, r in pitcheo.iterrows():
    emoji = "🟢" if r['score'] >= 70 else "🟡" if r['score'] >= 40 else "🔴"
    print(f"{emoji} {r['Name']:<20} {r['p_era']:>5.2f} {r['xera']:>6.2f} {r['p_strikeout']:>4.0f} {r['p_win']:>3.0f} {r['p_save']:>3.0f} {r['score']:>6.1f}")

print("\n" + "=" * 65)
print("ALERTAS DE LA SEMANA")
print("=" * 65)

mejorando = bateo[bateo['xwoba'] - bateo['woba'] > 0.020]
if len(mejorando) > 0:
    print("\n📈 COMPRAR - Jugadores que mejorarán (xwOBA > wOBA):")
    for _, r in mejorando.iterrows():
        diff = r['xwoba'] - r['woba']
        print(f"   {r['Name']}: xwOBA {r['xwoba']:.3f} vs wOBA {r['woba']:.3f} (+{diff:.3f})")

bajando = bateo[bateo['woba'] - bateo['xwoba'] > 0.020]
if len(bajando) > 0:
    print("\n📉 VENDER - Jugadores que bajarán (wOBA > xwOBA):")
    for _, r in bajando.iterrows():
        diff = r['woba'] - r['xwoba']
        print(f"   {r['Name']}: wOBA {r['woba']:.3f} vs xwOBA {r['xwoba']:.3f} (-{diff:.3f})")

riesgo_pit = pitcheo[pitcheo['xera'] - pitcheo['p_era'] > 0.50]
if len(riesgo_pit) > 0:
    print("\n⚠️  RIESGO - Pitchers con suerte (xERA >> ERA):")
    for _, r in riesgo_pit.iterrows():
        diff = r['xera'] - r['p_era']
        print(f"   {r['Name']}: ERA {r['p_era']:.2f} vs xERA {r['xera']:.2f} (+{diff:.2f})")

# ================================
# GUARDAR
# ================================
bateo.to_csv('data/scoring_bateadores.csv', index=False)
pitcheo.to_csv('data/scoring_pitchers.csv', index=False)
print("\n✅ Scoring guardado en data/")