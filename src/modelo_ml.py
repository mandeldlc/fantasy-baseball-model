import pandas as pd
import numpy as np
import sys
print(f"Python: {sys.version}")
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# ================================
# CARGAR DATOS HISTÓRICOS
# ================================

print("Cargando datos históricos 2022-2025...")
bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

# Arreglar nombres
bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

# ================================
# MODELO BATEADORES
# Predecir woba del año siguiente
# ================================

print("\nEntrenando modelo de bateadores...")

# Crear dataset: usar año N para predecir año N+1
bateo_model = []
for year in [2022, 2023, 2024]:
    curr = bateo[bateo['year'] == year].copy()
    next_year = bateo[bateo['year'] == year + 1][['Name', 'woba']].copy()
    next_year.columns = ['Name', 'woba_next']
    merged = curr.merge(next_year, on='Name')
    bateo_model.append(merged)

bateo_model = pd.concat(bateo_model, ignore_index=True)

# Features y target
features_bat = ['pa', 'home_run', 'on_base_plus_slg', 'woba', 
                'xwoba', 'xba', 'xslg', 'babip', 
                'exit_velocity_avg', 'barrel_batted_rate']
X_bat = bateo_model[features_bat].fillna(0)
y_bat = bateo_model['woba_next']

# Entrenar
X_train, X_test, y_train, y_test = train_test_split(X_bat, y_bat, test_size=0.2, random_state=42)
scaler_bat = StandardScaler()
X_train_s = scaler_bat.fit_transform(X_train)
X_test_s = scaler_bat.transform(X_test)

model_bat = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
model_bat.fit(X_train_s, y_train)
pred_bat = model_bat.predict(X_test_s)
mae_bat = mean_absolute_error(y_test, pred_bat)
print(f"  MAE Bateadores: {mae_bat:.4f} (error promedio en wOBA)")

# ================================
# MODELO PITCHERS
# Predecir xera del año siguiente
# ================================

print("\nEntrenando modelo de pitchers...")

pitcheo_model = []
for year in [2022, 2023, 2024]:
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
pred_pit = model_pit.predict(X_test_ps)
mae_pit = mean_absolute_error(y_test_p, pred_pit)
print(f"  MAE Pitchers: {mae_pit:.4f} (error promedio en xERA)")

# ================================
# PREDECIR TU ROSTER 2026
# ================================

print("\nPrediciendo rendimiento 2026 de tu roster...")

mis_bateadores = pd.read_csv('data/mis_bateadores_2025.csv')
mis_pitchers = pd.read_csv('data/mis_pitchers_2025.csv')

# Predicciones bateadores
X_mis_bat = mis_bateadores[features_bat].fillna(0)
X_mis_bat_s = scaler_bat.transform(X_mis_bat)
mis_bateadores['woba_pred_2026'] = model_bat.predict(X_mis_bat_s).round(3)

# Predicciones pitchers
X_mis_pit = mis_pitchers[features_pit].fillna(0)
X_mis_pit_s = scaler_pit.transform(X_mis_pit)
mis_pitchers['xera_pred_2026'] = model_pit.predict(X_mis_pit_s).round(2)

# Mostrar resultados
print("\n" + "=" * 65)
print("PREDICCIONES 2026 - BATEADORES")
print("=" * 65)
print(f"{'Jugador':<22} {'wOBA 2025':>10} {'wOBA pred 2026':>15} {'Tendencia':>10}")
print("-" * 65)
for _, r in mis_bateadores.sort_values('woba_pred_2026', ascending=False).iterrows():
    tendencia = "📈 Sube" if r['woba_pred_2026'] > r['woba'] else "📉 Baja"
    print(f"{r['Name']:<22} {r['woba']:>10.3f} {r['woba_pred_2026']:>15.3f} {tendencia:>10}")

print("\n" + "=" * 65)
print("PREDICCIONES 2026 - PITCHERS")
print("=" * 65)
print(f"{'Pitcher':<22} {'xERA 2025':>10} {'xERA pred 2026':>15} {'Tendencia':>10}")
print("-" * 65)
for _, r in mis_pitchers.sort_values('xera_pred_2026', ascending=True).iterrows():
    tendencia = "📈 Mejora" if r['xera_pred_2026'] < r['xera'] else "📉 Empeora"
    print(f"{r['Name']:<22} {r['xera']:>10.2f} {r['xera_pred_2026']:>15.2f} {tendencia:>10}")

# Guardar
mis_bateadores.to_csv('data/predicciones_bateadores_2026.csv', index=False)
mis_pitchers.to_csv('data/predicciones_pitchers_2026.csv', index=False)
print("\n✅ Predicciones guardadas en data/")

print("Script completado.")
sys.stdout.flush()