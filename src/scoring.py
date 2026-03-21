import pandas as pd
import numpy as np

# ================================
# SISTEMA DE PUNTUACIÓN SEMANAL
# ================================

bateo = pd.read_csv('data/mis_bateadores_2025.csv')
pitcheo = pd.read_csv('data/mis_pitchers_2025.csv')

# ================================
# SCORE BATEADORES
# Basado en las categorías de tu Yahoo:
# R, HR, RBI, SB, OBP, SLG
# Usamos los equivalentes que tenemos:
# HR, OPS, woba, xwoba, barrel_rate
# ================================

def score_bateador(row):
    score = 0
    score += row['home_run'] * 0.30          # HR es la categoría más importante
    score += row['on_base_plus_slg'] * 20    # OPS cubre OBP + SLG
    score += row['woba'] * 15                # woba = valor ofensivo total
    score += row['xwoba'] * 10              # xwoba = predicción futura
    score += row['barrel_batted_rate'] * 0.5 # contacto de calidad
    score += row['exit_velocity_avg'] * 0.1  # velocidad de contacto
    return round(score, 2)

def score_pitcher(row):
    score = 0
    score += (5 - row['p_era']) * 5         # ERA bajo = mejor
    score += (5 - row['xera']) * 3          # xera = predicción futura
    score += row['p_strikeout'] * 0.1       # Ks
    score += row['p_win'] * 2               # Wins
    score += row['p_save'] * 3              # Saves (NSV)
    score += (0.4 - row['xwoba']) * 20      # xwoba bajo = mejor pitcher
    score -= row['exit_velocity_avg'] * 0.1 # exit velo alto = malo para pitcher
    return round(score, 2)

bateo['score'] = bateo.apply(score_bateador, axis=1)
pitcheo['score'] = pitcheo.apply(score_pitcher, axis=1)

# Normalizar scores 0-100
bateo['score'] = ((bateo['score'] - bateo['score'].min()) / 
                  (bateo['score'].max() - bateo['score'].min()) * 100).round(1)
pitcheo['score'] = ((pitcheo['score'] - pitcheo['score'].min()) / 
                    (pitcheo['score'].max() - pitcheo['score'].min()) * 100).round(1)

bateo = bateo.sort_values('score', ascending=False)
pitcheo = pitcheo.sort_values('score', ascending=False)

print("=" * 65)
print("RECOMENDACIONES SEMANALES - BATEADORES")
print("=" * 65)
print(f"{'Jugador':<22} {'HR':>4} {'OPS':>6} {'wOBA':>6} {'xwOBA':>6} {'Score':>6}")
print("-" * 65)
for _, r in bateo.iterrows():
    emoji = "🟢" if r['score'] >= 70 else "🟡" if r['score'] >= 40 else "🔴"
    print(f"{emoji} {r['Name']:<20} {r['home_run']:>4} {r['on_base_plus_slg']:>6.3f} {r['woba']:>6.3f} {r['xwoba']:>6.3f} {r['score']:>6.1f}")

print("\n" + "=" * 65)
print("RECOMENDACIONES SEMANALES - PITCHERS")
print("=" * 65)
print(f"{'Pitcher':<22} {'ERA':>5} {'xERA':>6} {'Ks':>4} {'W':>3} {'SV':>3} {'Score':>6}")
print("-" * 65)
for _, r in pitcheo.iterrows():
    emoji = "🟢" if r['score'] >= 70 else "🟡" if r['score'] >= 40 else "🔴"
    print(f"{emoji} {r['Name']:<20} {r['p_era']:>5.2f} {r['xera']:>6.2f} {r['p_strikeout']:>4} {r['p_win']:>3} {r['p_save']:>3} {r['score']:>6.1f}")

print("\n" + "=" * 65)
print("ALERTAS DE LA SEMANA")
print("=" * 65)

# Jugadores con xwoba mucho mayor que woba = van a mejorar
mejorando = bateo[bateo['xwoba'] - bateo['woba'] > 0.020]
if len(mejorando) > 0:
    print("\n📈 COMPRAR - Jugadores que mejorarán (xwOBA > wOBA):")
    for _, r in mejorando.iterrows():
        diff = r['xwoba'] - r['woba']
        print(f"   {r['Name']}: xwOBA {r['xwoba']:.3f} vs wOBA {r['woba']:.3f} (+{diff:.3f})")

# Jugadores con woba mucho mayor que xwoba = van a bajar
bajando = bateo[bateo['woba'] - bateo['xwoba'] > 0.020]
if len(bajando) > 0:
    print("\n📉 VENDER - Jugadores que bajarán (wOBA > xwOBA):")
    for _, r in bajando.iterrows():
        diff = r['woba'] - r['xwoba']
        print(f"   {r['Name']}: wOBA {r['woba']:.3f} vs xwOBA {r['xwoba']:.3f} (-{diff:.3f})")

# Pitchers con xera mucho mayor que era = van a empeorar
riesgo_pit = pitcheo[pitcheo['xera'] - pitcheo['p_era'] > 0.50]
if len(riesgo_pit) > 0:
    print("\n⚠️  RIESGO - Pitchers con suerte (xERA >> ERA):")
    for _, r in riesgo_pit.iterrows():
        diff = r['xera'] - r['p_era']
        print(f"   {r['Name']}: ERA {r['p_era']:.2f} vs xERA {r['xera']:.2f} (+{diff:.2f})")

# Guardar
bateo.to_csv('data/scoring_bateadores.csv', index=False)
pitcheo.to_csv('data/scoring_pitchers.csv', index=False)
print("\n✅ Scoring guardado en data/")