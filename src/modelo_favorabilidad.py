import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, accuracy_score
import pickle
import warnings
warnings.filterwarnings('ignore')

print("Entrenando modelo de favorabilidad pitcher vs equipo...")

# ================================
# CARGAR DATOS
# ================================
pitcheo = pd.read_csv('data/pitcheo_historico.csv')
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

pitcheo_av = []
for year in [2022, 2023, 2024, 2025]:
    p = pd.read_csv(f'data/pitcheo_avanzado_{year}.csv')
    p['year'] = year
    p[['last_name', 'first_name']] = p['last_name, first_name'].str.split(', ', expand=True)
    p['Name'] = p['first_name'] + ' ' + p['last_name']
    pitcheo_av.append(p)
pitcheo_av = pd.concat(pitcheo_av, ignore_index=True)

team_offense = pd.read_csv('data/team_offense.csv')
matchup_hist = pd.read_csv('data/favorabilidad_pitcher_equipo.csv')

# Solo usar registros con historial real
matchup_hist = matchup_hist[
    (matchup_hist['PA_hist'] >= 10) &
    (matchup_hist['xwOBA_hist'].notna()) &
    (matchup_hist['EV_hist'].notna())
].copy()

print(f"  ✅ Matchups históricos: {len(matchup_hist)}")

# ================================
# CONSTRUIR DATASET CORRECTO
# Features: stats del pitcher + stats del equipo
# Target: xwOBA que el pitcher permitió a ese equipo (real histórico)
# ================================
print("Construyendo dataset...")

features_pit = [f for f in [
    'k_percent', 'bb_percent', 'whiff_percent',
    'f_strike_percent', 'in_zone_percent',
    'ff_avg_speed', 'fastball_avg_speed',
    'z_swing_miss_percent', 'oz_swing_miss_percent'
] if f in pitcheo_av.columns]

features_team = ['woba', 'xwoba', 'exit_velocity', 'barrel_rate', 'hard_hit', 'obp', 'slg']

pit_2025 = pitcheo[pitcheo['year'] == 2025].copy()
pit_av_2025 = pitcheo_av[pitcheo_av['year'] == 2025].copy()
team_2025 = team_offense[team_offense['year'] == 2025].copy()

dataset = []
for _, match in matchup_hist.iterrows():
    nombre = match['Name']
    oponente = match['Oponente']

    pit_stats = pit_2025[pit_2025['Name'] == nombre]
    pit_av_stats = pit_av_2025[pit_av_2025['Name'] == nombre]
    team_stats = team_2025[team_2025['team_name'] == oponente]

    if len(pit_stats) == 0 or len(team_stats) == 0:
        continue

    p = pit_stats.iloc[0]
    p_av = pit_av_stats.iloc[0] if len(pit_av_stats) > 0 else pd.Series()
    t = team_stats.iloc[0]

    row = {
        'xera': p.get('xera', 4.0),
        'p_xwoba': p.get('xwoba', 0.320),
        'p_ev': p.get('exit_velocity_avg', 89.0),
        'p_barrel': p.get('barrel_batted_rate', 8.0),
        'p_whip': p.get('p_whip', 1.3),
    }
    for f in features_pit:
        row[f'pit_{f}'] = float(p_av.get(f, 0)) if len(p_av) > 0 else 0
    for f in features_team:
        row[f'team_{f}'] = t.get(f, 0)
    row['team_offense_score'] = t.get('offense_score_norm', 50.0)

    # Target correcto: xwOBA real que el pitcher permitió a ese equipo
    row['target_xwoba'] = match['xwOBA_hist']
    row['target_ev'] = match['EV_hist']
    # Clasificación: favorable si xwOBA < 0.310
    row['target_favorable'] = 1 if match['xwOBA_hist'] < 0.310 else 0

    dataset.append(row)

df = pd.DataFrame(dataset).fillna(0)
print(f"  ✅ Dataset: {len(df)} matchups reales")

if len(df) < 10:
    print("  ⚠️ Pocos datos — usando modelo simplificado basado en reglas")
    # Guardar modelo vacío
    with open('data/modelo_favorabilidad.pkl', 'wb') as f:
        pickle.dump({'mode': 'rules'}, f)
else:
    feature_cols = (
        ['xera', 'p_xwoba', 'p_ev', 'p_barrel', 'p_whip'] +
        [f'pit_{f}' for f in features_pit] +
        [f'team_{f}' for f in features_team] +
        ['team_offense_score']
    )
    feature_cols = [f for f in feature_cols if f in df.columns]

    X = df[feature_cols].fillna(0)
    y_xwoba = df['target_xwoba']
    y_fav = df['target_favorable']

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_s, y_xwoba, test_size=0.2, random_state=42)
    X_train_f, X_test_f, y_train_f, y_test_f = train_test_split(X_s, y_fav, test_size=0.2, random_state=42)

    # Modelo 1 — Predecir xwOBA esperada
    print("\nEntrenando GradientBoosting xwOBA...")
    model_xwoba = GradientBoostingRegressor(
        n_estimators=100, learning_rate=0.05,
        max_depth=3, random_state=42, subsample=0.8
    )
    model_xwoba.fit(X_train, y_train)
    mae = mean_absolute_error(y_test, model_xwoba.predict(X_test))
    print(f"  MAE xwOBA: {mae:.4f}")

    # Modelo 2 — Clasificación favorable
    print("Entrenando RandomForest clasificación...")
    model_fav = RandomForestClassifier(
        n_estimators=100, max_depth=4,
        random_state=42, min_samples_leaf=3
    )
    model_fav.fit(X_train_f, y_train_f)
    acc = accuracy_score(y_test_f, model_fav.predict(X_test_f))
    print(f"  Accuracy: {acc:.3f}")

    with open('data/modelo_favorabilidad.pkl', 'wb') as f:
        pickle.dump({
            'mode': 'ml',
            'model_xwoba': model_xwoba,
            'model_fav': model_fav,
            'scaler': scaler,
            'feature_cols': feature_cols
        }, f)
    print("\n✅ Modelos guardados")

    # ================================
    # PREDECIR ESTA SEMANA
    # ================================
    print("\nCalculando favorabilidad para esta semana...")
    matchup_semana = pd.read_csv('data/favorabilidad_pitcher_equipo.csv')

    resultados = []
    for _, row in matchup_semana.iterrows():
        nombre = row['Name']
        oponente = row['Oponente']

        pit_stats = pit_2025[pit_2025['Name'] == nombre]
        pit_av_stats = pit_av_2025[pit_av_2025['Name'] == nombre]
        team_stats = team_2025[team_2025['team_name'] == oponente]

        if len(pit_stats) == 0 or len(team_stats) == 0:
            continue

        p = pit_stats.iloc[0]
        p_av = pit_av_stats.iloc[0] if len(pit_av_stats) > 0 else pd.Series()
        t = team_stats.iloc[0]

        feat = {
            'xera': p.get('xera', 4.0),
            'p_xwoba': p.get('xwoba', 0.320),
            'p_ev': p.get('exit_velocity_avg', 89.0),
            'p_barrel': p.get('barrel_batted_rate', 8.0),
            'p_whip': p.get('p_whip', 1.3),
        }
        for f in features_pit:
            feat[f'pit_{f}'] = float(p_av.get(f, 0)) if len(p_av) > 0 else 0
        for f in features_team:
            feat[f'team_{f}'] = t.get(f, 0)
        feat['team_offense_score'] = t.get('offense_score_norm', 50.0)

        X_pred = pd.DataFrame([feat])[feature_cols].fillna(0)
        X_pred_s = scaler.transform(X_pred)

        xwoba_pred = model_xwoba.predict(X_pred_s)[0]
        prob_fav = model_fav.predict_proba(X_pred_s)[0][1]

        # Si tenemos historial real, hacer blend 70% historial + 30% modelo
        if row['PA_hist'] >= 50 and pd.notna(row['xwOBA_hist']):
            xwoba_final = round(0.70 * row['xwOBA_hist'] + 0.30 * xwoba_pred, 3)
            fuente = 'Hist+ML'
        else:
            xwoba_final = round(xwoba_pred, 3)
            fuente = 'ML'

        clasif = '🟢 Favorable' if xwoba_final < 0.300 else '🔴 Difícil' if xwoba_final > 0.330 else '🟡 Normal'

        resultados.append({
            'Name': nombre,
            'Oponente': oponente,
            'xwOBA_pred': xwoba_final,
            'Prob_favorable': round(prob_fav * 100, 1),
            'Clasificacion': clasif,
            'Fuente_pred': fuente,
            'xwOBA_hist': row.get('xwOBA_hist', None),
            'PA_hist': row.get('PA_hist', 0),
            'xERA_2025': round(float(p.get('xera', 0)), 2)
        })

    df_fav = pd.DataFrame(resultados).sort_values('xwOBA_pred', ascending=True)
    df_fav.to_csv('data/favorabilidad_semana.csv', index=False)

    print("\n" + "=" * 75)
    print("FAVORABILIDAD PITCHER vs EQUIPO — ESTA SEMANA")
    print("=" * 75)
    print(f"{'Pitcher':<22} {'Oponente':<25} {'xwOBA pred':>10} {'Prob%':>6} {'Clasif':>12} {'Fuente':>8}")
    print("-" * 75)
    for _, r in df_fav.iterrows():
        xwoba_hist = f"{r['xwOBA_hist']:.3f}" if pd.notna(r['xwOBA_hist']) else 'N/A'
        print(f"{r['Name']:<22} {r['Oponente']:<25} {r['xwOBA_pred']:>10.3f} {r['Prob_favorable']:>6.1f} {r['Clasificacion']:>12} {r['Fuente_pred']:>8}")

    print(f"\n✅ Guardado en data/favorabilidad_semana.csv")