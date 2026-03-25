import pandas as pd
import requests

print("Identificando closers confirmados...")

# ================================
# CARGAR DATOS
# ================================
pitcheo = pd.read_csv('data/pitcheo_historico.csv')
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

waivers_rp = pd.read_csv('data/waivers_rp.csv')
waivers_rp = waivers_rp[waivers_rp['Name'].notna()]

# Stats 2025
pit_2025 = pitcheo[pitcheo['year'] == 2025]
pit_2024 = pitcheo[pitcheo['year'] == 2024]

# ================================
# IDENTIFICAR CLOSERS
# ================================
# Closer = RP con saves + oportunidades consistentes
# Usamos saves 2024 y 2025 como señal

closers = []

for _, row in waivers_rp.iterrows():
    nombre = row['Name']

    stats_2025 = pit_2025[pit_2025['Name'] == nombre]
    stats_2024 = pit_2024[pit_2024['Name'] == nombre]

    sv_2025 = stats_2025['p_save'].values[0] if len(stats_2025) > 0 else 0
    sv_2024 = stats_2024['p_save'].values[0] if len(stats_2024) > 0 else 0

    era_2025 = stats_2025['p_era'].values[0] if len(stats_2025) > 0 else 99
    xera_2025 = stats_2025['xera'].values[0] if len(stats_2025) > 0 else 99
    xwoba_2025 = stats_2025['xwoba'].values[0] if len(stats_2025) > 0 else 0.400

    # Score de closer
    closer_score = 0
    tipo = []

    if sv_2025 >= 20:
        closer_score += 5
        tipo.append(f"Closer élite 2025 ({sv_2025} SV)")
    elif sv_2025 >= 10:
        closer_score += 3
        tipo.append(f"Closer 2025 ({sv_2025} SV)")
    elif sv_2025 >= 5:
        closer_score += 2
        tipo.append(f"Oportunidades 2025 ({sv_2025} SV)")

    if sv_2024 >= 20:
        closer_score += 3
        tipo.append(f"Historial 2024 ({sv_2024} SV)")
    elif sv_2024 >= 10:
        closer_score += 2
        tipo.append(f"Historial 2024 ({sv_2024} SV)")

    if era_2025 < 3.0:
        closer_score += 2
        tipo.append(f"ERA élite {era_2025:.2f}")
    elif era_2025 < 3.50:
        closer_score += 1

    if xera_2025 < 3.0:
        closer_score += 2
        tipo.append(f"xERA élite {xera_2025:.2f}")

    if closer_score >= 2:
        closers.append({
            'Name': nombre,
            'SV_2025': sv_2025,
            'SV_2024': sv_2024,
            'ERA': era_2025,
            'xERA': xera_2025,
            'xwOBA': xwoba_2025,
            'Closer_Score': closer_score,
            'Tipo': ' | '.join(tipo),
            'breakout_score': row.get('breakout_score', 0)
        })

df_closers = pd.DataFrame(closers).sort_values('Closer_Score', ascending=False) if closers else pd.DataFrame()
df_closers.to_csv('data/closers.csv', index=False)

print("\n" + "=" * 70)
print("🔒 CLOSERS CONFIRMADOS EN WAIVERS")
print("=" * 70)
if len(df_closers) > 0:
    for _, r in df_closers.iterrows():
        print(f"  🔒 {r['Name']}: SV25={r['SV_2025']:.0f} SV24={r['SV_2024']:.0f} ERA={r['ERA']:.2f} xERA={r['xERA']:.2f} Score={r['Closer_Score']}")
        print(f"     {r['Tipo']}")
else:
    print("  Ninguno detectado")

print(f"\n✅ {len(df_closers)} closers guardados en data/closers.csv")