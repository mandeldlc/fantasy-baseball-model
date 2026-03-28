import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_curr_data
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

SEASON = get_season()
SEASON_PREV = SEASON - 1

print(f"Cargando datos históricos para predicciones {SEASON}...")

bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

# ================================
# MODELO BATEADORES
# ================================
print("\nEntrenando modelo de bateadores...")

bateo_model = []
for year in [SEASON-3, SEASON-2, SEASON-1]:
    curr = bateo[bateo['year'] == year].copy()
    next_year = bateo[bateo['year'] == year + 1][['Name', 'woba']].copy()
    next_year.columns = ['Name', 'woba_next']
    merged = curr.merge(next_year, on='Name')
    bateo_model.append(merged)

bateo_model = pd.concat(bateo_model, ignore_index=True)

features_bat = ['pa', 'home_run', 'on_base_plus_slg', 'woba',
                'xwoba', 'xba', 'xslg', 'babip',
                'exit_velocity_avg', 'barrel_batted_rate']
X_bat = bateo_model[features_bat].fillna(0)
y_bat = bateo_model['woba_next']

X_train, X_test, y_train, y_test = train_test_split(X_bat, y_bat, test_size=0.2, random_state=42)
scaler_bat = StandardScaler()
X_train_s = scaler_bat.fit_transform(X_train)
X_test_s = scaler_bat.transform(X_test)

model_bat = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
model_bat.fit(X_train_s, y_train)
mae_bat = mean_absolute_error(y_test, model_bat.predict(X_test_s))
print(f"  MAE Bateadores: {mae_bat:.4f}")

# ================================
# MODELO PITCHERS
# ================================
print("\nEntrenando modelo de pitchers...")

pitcheo_model = []
for year in [SEASON-3, SEASON-2, SEASON-1]:
    curr = pitcheo[pitcheo['year'] == year].copy()
    next_year = pitcheo[pitcheo['year'] == year + 1][['Name', 'xera']].copy()
    next_year.columns = ['Name', 'xera_next']
    merged = curr.merge(next_year, on='Name')
    pitcheo_model.append(merged)

pitcheo_model = pd.concat(pitcheo_model, ignore_index=True)

features_pit = ['p_era', 'xera', 'p_strikeout', 'p_win',
                'p_save', 'xwoba', 'exit_velocity_avg']
X_pit = pitcheo_model[features_pit].fillna(0)
y_pit = pitcheo_model['xera_next']

X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(X_pit, y_pit, test_size=0.2, random_state=42)
scaler_pit = StandardScaler()
X_train_ps = scaler_pit.fit_transform(X_train_p)
X_test_ps = scaler_pit.transform(X_test_p)

model_pit = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
model_pit.fit(X_train_ps, y_train_p)
mae_pit = mean_absolute_error(y_test_p, model_pit.predict(X_test_ps))
print(f"  MAE Pitchers: {mae_pit:.4f}")

# ================================
# CARGAR ROSTER ACTUAL
# ================================
roster = pd.read_csv('data/roster.csv')
mis_bateadores_list = roster[~roster['Pos'].isin(['SP', 'RP', 'P'])]['Name'].tolist()
mis_pitchers_list = roster[roster['Pos'].isin(['SP', 'RP', 'P', 'IL', 'BN'])]['Name'].tolist()

# Data actual con fallback al año anterior
bat_curr = bateo[bateo['year'] == SEASON].copy()
bat_prev = bateo[bateo['year'] == SEASON_PREV].copy()
bat_faltantes = bat_prev[~bat_prev['Name'].isin(set(bat_curr['Name']))]
bat_data = pd.concat([bat_curr, bat_faltantes], ignore_index=True)

pit_curr = pitcheo[pitcheo['year'] == SEASON].copy()
pit_prev = pitcheo[pitcheo['year'] == SEASON_PREV].copy()
pit_faltantes = pit_prev[~pit_prev['Name'].isin(set(pit_curr['Name']))]
pit_data = pd.concat([pit_curr, pit_faltantes], ignore_index=True)

mis_bateadores = bat_data[bat_data['Name'].isin(mis_bateadores_list)].copy()
mis_pitchers = pit_data[pit_data['Name'].isin(mis_pitchers_list)].copy()

print(f"\nRoster actual: {len(mis_bateadores)} bateadores, {len(mis_pitchers)} pitchers")

# ================================
# PREDICCIONES
# ================================
if len(mis_bateadores) > 0:
    X_mis_bat = mis_bateadores[features_bat].fillna(0)
    X_mis_bat_s = scaler_bat.transform(X_mis_bat)
    mis_bateadores['woba_pred_2026'] = model_bat.predict(X_mis_bat_s).round(3)
    mis_bateadores['woba'] = mis_bateadores['woba'].round(3)

if len(mis_pitchers) > 0:
    X_mis_pit = mis_pitchers[features_pit].fillna(0)
    X_mis_pit_s = scaler_pit.transform(X_mis_pit)
    mis_pitchers['xera_pred_2026'] = model_pit.predict(X_mis_pit_s).round(2)
    mis_pitchers['xera'] = mis_pitchers['xera'].round(2)

# ================================
# MOSTRAR
# ================================
print("\n" + "=" * 65)
print(f"PREDICCIONES {SEASON} - BATEADORES")
print("=" * 65)
print(f"{'Jugador':<22} {'wOBA prev':>10} {'wOBA pred':>15} {'Tendencia':>10}")
print("-" * 65)
for _, r in mis_bateadores.sort_values('woba_pred_2026', ascending=False).iterrows():
    tendencia = "📈 Sube" if r['woba_pred_2026'] > r['woba'] else "📉 Baja"
    print(f"{r['Name']:<22} {r['woba']:>10.3f} {r['woba_pred_2026']:>15.3f} {tendencia:>10}")

print("\n" + "=" * 65)
print(f"PREDICCIONES {SEASON} - PITCHERS")
print("=" * 65)
print(f"{'Pitcher':<22} {'xERA prev':>10} {'xERA pred':>15} {'Tendencia':>10}")
print("-" * 65)
for _, r in mis_pitchers.sort_values('xera_pred_2026', ascending=True).iterrows():
    tendencia = "📈 Mejora" if r['xera_pred_2026'] < r['xera'] else "📉 Empeora"
    print(f"{r['Name']:<22} {r['xera']:>10.2f} {r['xera_pred_2026']:>15.2f} {tendencia:>10}")

# ================================
# GUARDAR
# ================================
mis_bateadores.to_csv('data/predicciones_bateadores_2026.csv', index=False)
mis_pitchers.to_csv('data/predicciones_pitchers_2026.csv', index=False)
print("\n✅ Predicciones guardadas en data/")