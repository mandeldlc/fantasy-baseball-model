import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
from sklearn.inspection import permutation_importance
import warnings
warnings.filterwarnings('ignore')

# ================================
# CARGAR Y COMBINAR DATOS AVANZADOS
# ================================
print("Cargando datos avanzados 2022-2025...")

all_bat = []
all_pit = []

for year in [2022, 2023, 2024, 2025]:
    b = pd.read_csv(f'data/bateo_avanzado_{year}.csv')
    b['year'] = year
    all_bat.append(b)
    
    p = pd.read_csv(f'data/pitcheo_avanzado_{year}.csv')
    p['year'] = year
    all_pit.append(p)

bateo = pd.concat(all_bat, ignore_index=True)
pitcheo = pd.concat(all_pit, ignore_index=True)

# Arreglar nombres
bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']

pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

print(f"✅ Bateadores: {len(bateo)} registros")
print(f"✅ Pitchers: {len(pitcheo)} registros")

# ================================
# FEATURES BATEADORES
# ================================
features_bat = [
    'xba', 'xslg', 'xwoba', 'xobp', 'xiso',
    'xbadiff', 'xslgdiff',
    'avg_swing_speed', 'fast_swing_rate',
    'blasts_contact', 'blasts_swing',
    'squared_up_contact', 'squared_up_swing',
    'attack_angle', 'ideal_angle_rate',
    'barrel_batted_rate', 'hard_hit_percent',
    'sweet_spot_percent', 'exit_velocity_avg',
    'babip', 'isolated_power', 'on_base_plus_slg',
    'pa', 'player_age',
    'r_total_stolen_base', 'on_base_percent',
    'slg_percent', 'b_rbi'
]

# Target: Fantasy Score ponderado
# R + HR*4 + RBI*2 + SB*3 + OBP*50 + SLG*30
def calc_fantasy_score_bat(df):
    return (
        df['home_run'] * 4 +
        df['b_rbi'] * 2 +
        df['r_total_stolen_base'] * 3 +
        df['on_base_percent'] * 50 +
        df['slg_percent'] * 30 +
        df['woba'] * 40
    )

bateo['fantasy_score'] = calc_fantasy_score_bat(bateo)

# ================================
# MODELO BATEADORES
# ================================
print("\nEntrenando modelo avanzado de bateadores...")

bat_model_data = []
for year in [2022, 2023, 2024]:
    curr = bateo[bateo['year'] == year].copy()
    next_yr = bateo[bateo['year'] == year + 1][['Name', 'fantasy_score']].copy()
    next_yr.columns = ['Name', 'fantasy_score_next']
    merged = curr.merge(next_yr, on='Name')
    bat_model_data.append(merged)

bat_df = pd.concat(bat_model_data, ignore_index=True)

X_bat = bat_df[features_bat].fillna(0)
y_bat = bat_df['fantasy_score_next']

X_train, X_test, y_train, y_test = train_test_split(X_bat, y_bat, test_size=0.2, random_state=42)
scaler_bat = StandardScaler()
X_train_s = scaler_bat.fit_transform(X_train)
X_test_s = scaler_bat.transform(X_test)

model_bat = GradientBoostingRegressor(
    n_estimators=200, learning_rate=0.05, 
    max_depth=4, random_state=42
)
model_bat.fit(X_train_s, y_train)
mae_bat = mean_absolute_error(y_test, model_bat.predict(X_test_s))
print(f"  MAE Bateadores: {mae_bat:.2f} (fantasy score)")

# Feature importance bateadores
importance_bat = pd.DataFrame({
    'feature': features_bat,
    'importance': model_bat.feature_importances_
}).sort_values('importance', ascending=False)
print("\n  Top 10 variables más importantes (bateadores):")
print(importance_bat.head(10).to_string(index=False))

# ================================
# FEATURES PITCHERS
# ================================
features_pit = [
    'k_percent', 'bb_percent',
    'whiff_percent', 'z_swing_miss_percent', 'oz_swing_miss_percent',
    'f_strike_percent', 'in_zone_percent',
    'ff_avg_speed', 'ff_avg_spin',
    'fastball_avg_speed', 'fastball_avg_spin',
    'p_era', 'p_opp_batting_avg'
]
features_pit = [f for f in features_pit if f in pitcheo.columns]

# Target: Fantasy Score pitchers
# K*2 + W*5 + SV*4 - ERA*10 - BB*1
def calc_fantasy_score_pit(df):
    era_col = 'p_era' if 'p_era' in df.columns else 'era'
    score = df['k_percent'] * 50
    if 'p_win' in df.columns:
        score += df['p_win'] * 5
    if era_col in df.columns:
        score -= df[era_col] * 10
    return score

pitcheo['fantasy_score'] = calc_fantasy_score_pit(pitcheo)

# ================================
# MODELO PITCHERS
# ================================
print("\nEntrenando modelo avanzado de pitchers...")

pit_model_data = []
for year in [2022, 2023, 2024]:
    curr = pitcheo[pitcheo['year'] == year].copy()
    next_yr = pitcheo[pitcheo['year'] == year + 1][['Name', 'fantasy_score']].copy()
    next_yr.columns = ['Name', 'fantasy_score_next']
    merged = curr.merge(next_yr, on='Name')
    pit_model_data.append(merged)

pit_df = pd.concat(pit_model_data, ignore_index=True)

X_pit = pit_df[features_pit].fillna(0)
y_pit = pit_df['fantasy_score_next']

X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(X_pit, y_pit, test_size=0.2, random_state=42)
scaler_pit = StandardScaler()
X_train_ps = scaler_pit.fit_transform(X_train_p)
X_test_ps = scaler_pit.transform(X_test_p)

model_pit = GradientBoostingRegressor(
    n_estimators=200, learning_rate=0.05,
    max_depth=4, random_state=42
)
model_pit.fit(X_train_ps, y_train_p)
mae_pit = mean_absolute_error(y_test_p, model_pit.predict(X_test_ps))
print(f"  MAE Pitchers: {mae_pit:.2f} (fantasy score)")

importance_pit = pd.DataFrame({
    'feature': features_pit,
    'importance': model_pit.feature_importances_
}).sort_values('importance', ascending=False)
print("\n  Top 10 variables más importantes (pitchers):")
print(importance_pit.head(10).to_string(index=False))

# ================================
# PREDICCIÓN PRÓXIMOS 7 DÍAS - TU ROSTER
# ================================
print("\n" + "=" * 65)
print("PROYECCIÓN SEMANAL — TU ROSTER")
print("=" * 65)

roster = pd.read_csv('data/roster.csv')
mis_jugadores = roster['Name'].tolist()

from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_blend_weights

SEASON = get_season()
SEASON_PREV = SEASON - 1
W_HIST, W_CURR = get_blend_weights()

# Usar blend de temporada actual + anterior
bat_curr = bateo[bateo['year'] == SEASON].copy()
bat_prev = bateo[bateo['year'] == SEASON_PREV].copy()
pit_curr = pitcheo[pitcheo['year'] == SEASON].copy()
pit_prev = pitcheo[pitcheo['year'] == SEASON_PREV].copy()

# Si hay suficiente data 2026, hacer blend
def blend_df(curr, prev, stat_cols):
    if len(curr) < 10:
        return prev
    curr_names = set(curr['Name'])
    rows = []
    for _, r in prev.iterrows():
        if r['Name'] in curr_names:
            r_curr = curr[curr['Name'] == r['Name']].iloc[0]
            blended = r.copy()
            for col in stat_cols:
                if col in r and col in r_curr and pd.notna(r[col]) and pd.notna(r_curr[col]):
                    blended[col] = round(W_HIST * r[col] + W_CURR * r_curr[col], 3)
            rows.append(blended)
        else:
            rows.append(r)
    solo_curr = curr[~curr['Name'].isin(set(prev['Name']))]
    return pd.concat([pd.DataFrame(rows), solo_curr], ignore_index=True)

bat_stat_cols = ['woba', 'xwoba', 'exit_velocity_avg', 'barrel_batted_rate', 'babip', 'on_base_percent', 'slg_percent']
pit_stat_cols = ['p_era', 'xera', 'xwoba', 'exit_velocity_avg', 'barrel_batted_rate']

bat_2025 = blend_df(bat_curr, bat_prev, bat_stat_cols)
pit_2025 = blend_df(pit_curr, pit_prev, pit_stat_cols)

print(f"  Data blend {SEASON_PREV}/{SEASON}: {len(bat_2025)} bateadores, {len(pit_2025)} pitchers")

# Bateadores
mis_bat = bat_2025[bat_2025['Name'].isin(mis_jugadores)].copy()
if len(mis_bat) > 0:
    X_mis = mis_bat[features_bat].fillna(0)
    X_mis_s = scaler_bat.transform(X_mis)
    mis_bat['fantasy_score_actual'] = calc_fantasy_score_bat(mis_bat)
    mis_bat['fantasy_score_proyectado'] = model_bat.predict(X_mis_s)
    mis_bat['tendencia'] = mis_bat.apply(
        lambda r: '📈' if r['fantasy_score_proyectado'] > r['fantasy_score_actual']
        else '📉', axis=1
    )

    print("\n🏏 BATEADORES")
    print(f"{'Jugador':<22} {'Score actual':>13} {'Proyección 7d':>14} {'Tendencia':>10}")
    print("-" * 65)
    for _, r in mis_bat.sort_values('fantasy_score_proyectado', ascending=False).iterrows():
        print(f"{r['Name']:<22} {r['fantasy_score_actual']:>13.1f} {r['fantasy_score_proyectado']:>14.1f} {r['tendencia']:>10}")

# Pitchers
mis_pit = pit_2025[pit_2025['Name'].isin(mis_jugadores)].copy()
if len(mis_pit) > 0:
    X_mis_p = mis_pit[features_pit].fillna(0)
    X_mis_ps = scaler_pit.transform(X_mis_p)
    mis_pit['fantasy_score_actual'] = calc_fantasy_score_pit(mis_pit)
    mis_pit['fantasy_score_proyectado'] = model_pit.predict(X_mis_ps)
    mis_pit['tendencia'] = mis_pit.apply(
        lambda r: '📈' if r['fantasy_score_proyectado'] > r['fantasy_score_actual']
        else '📉', axis=1
    )

    print("\n⚾ PITCHERS")
    print(f"{'Pitcher':<22} {'Score actual':>13} {'Proyección 7d':>14} {'Tendencia':>10}")
    print("-" * 65)
    for _, r in mis_pit.sort_values('fantasy_score_proyectado', ascending=False).iterrows():
        print(f"{r['Name']:<22} {r['fantasy_score_actual']:>13.1f} {r['fantasy_score_proyectado']:>14.1f} {r['tendencia']:>10}")

# Guardar
mis_bat.to_csv('data/proyeccion_semanal_bat.csv', index=False)
mis_pit.to_csv('data/proyeccion_semanal_pit.csv', index=False)
print("\n✅ Proyecciones guardadas en data/")