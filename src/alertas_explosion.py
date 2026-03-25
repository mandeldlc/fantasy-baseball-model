import pandas as pd
import numpy as np

print("Detectando jugadores a punto de explotar...")

# ================================
# CARGAR DATOS
# ================================
bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_2025 = bateo[bateo['year'] == 2025]
pitcheo_2025 = pitcheo[pitcheo['year'] == 2025]

waivers_bat = pd.read_csv('data/waivers_bateadores.csv')
waivers_sp = pd.read_csv('data/waivers_sp.csv')
waivers_rp = pd.read_csv('data/waivers_rp.csv')

# Excluir jugadores NA
waivers_bat = waivers_bat[waivers_bat['Name'].notna()]
waivers_sp = waivers_sp[waivers_sp['Name'].notna()]
waivers_rp = waivers_rp[waivers_rp['Name'].notna()]

# ================================
# ALERTAS BATEADORES
# ================================
def analizar_bateador(nombre, stats):
    if len(stats) == 0:
        return None

    s = stats.iloc[0]
    señales = []
    score_explosion = 0

    # Señal 1: xwOBA >> wOBA (mala suerte en resultados)
    diff_xwoba = s.get('xwoba', 0) - s.get('woba', 0)
    if diff_xwoba > 0.030:
        señales.append(f"xwOBA supera wOBA en +{diff_xwoba:.3f}")
        score_explosion += 3
    elif diff_xwoba > 0.020:
        señales.append(f"xwOBA supera wOBA en +{diff_xwoba:.3f}")
        score_explosion += 2

    # Señal 2: BABIP bajo (hits no están cayendo)
    babip = s.get('babip', 0.300)
    if babip < 0.250:
        señales.append(f"BABIP muy bajo {babip:.3f} — hits no caen")
        score_explosion += 3
    elif babip < 0.270:
        señales.append(f"BABIP bajo {babip:.3f}")
        score_explosion += 2

    # Señal 3: Exit velocity alto (conecta duro)
    ev = s.get('exit_velocity_avg', 0)
    if ev > 92:
        señales.append(f"EV élite {ev:.1f} mph")
        score_explosion += 3
    elif ev > 90:
        señales.append(f"EV alto {ev:.1f} mph")
        score_explosion += 2

    # Señal 4: Barrel rate alto
    barrel = s.get('barrel_batted_rate', 0)
    if barrel > 12:
        señales.append(f"Barrel rate élite {barrel:.1f}%")
        score_explosion += 3
    elif barrel > 9:
        señales.append(f"Barrel rate alto {barrel:.1f}%")
        score_explosion += 2

    # Señal 5: xBA >> BA
    xba = s.get('xba', 0)
    ba = s.get('batting_avg', 0)
    if xba > 0 and ba > 0 and (xba - ba) > 0.030:
        señales.append(f"xBA {xba:.3f} supera BA {ba:.3f}")
        score_explosion += 2

    return {
        'Name': nombre,
        'Señales': len(señales),
        'Score_Explosion': score_explosion,
        'Detalle': ' | '.join(señales),
        'wOBA': round(s.get('woba', 0), 3),
        'xwOBA': round(s.get('xwoba', 0), 3),
        'BABIP': round(babip, 3),
        'EV': round(ev, 1),
        'Barrel%': round(barrel, 1),
        'diff_xwoba': round(diff_xwoba, 3)
    }

# Analizar waivers bateadores
print("\nAnalizando bateadores en waivers...")
alertas_bat = []
for _, row in waivers_bat.iterrows():
    nombre = row['Name']
    stats = bateo_2025[bateo_2025['Name'] == nombre]
    resultado = analizar_bateador(nombre, stats)
    if resultado and resultado['Señales'] >= 3:
        alertas_bat.append(resultado)

df_alertas_bat = pd.DataFrame(alertas_bat).sort_values('Score_Explosion', ascending=False) if alertas_bat else pd.DataFrame()

# ================================
# ALERTAS PITCHERS
# ================================
def analizar_pitcher(nombre, stats):
    if len(stats) == 0:
        return None

    s = stats.iloc[0]
    señales = []
    score_explosion = 0

    # Señal 1: ERA >> xERA (mala suerte)
    era = s.get('p_era', 0)
    xera = s.get('xera', 0)
    diff_era = era - xera
    if diff_era > 1.5:
        señales.append(f"ERA {era:.2f} pero xERA {xera:.2f} — diferencia +{diff_era:.2f}")
        score_explosion += 3
    elif diff_era > 1.0:
        señales.append(f"ERA {era:.2f} pero xERA {xera:.2f} — diferencia +{diff_era:.2f}")
        score_explosion += 2

    # Señal 2: xwOBA bajo (domina el contacto)
    xwoba = s.get('xwoba', 0)
    if xwoba < 0.280:
        señales.append(f"xwOBA élite {xwoba:.3f} — domina contacto")
        score_explosion += 3
    elif xwoba < 0.300:
        señales.append(f"xwOBA bajo {xwoba:.3f}")
        score_explosion += 2

    # Señal 3: EV permitida baja
    ev = s.get('exit_velocity_avg', 0)
    if ev < 87:
        señales.append(f"EV permitida baja {ev:.1f} mph")
        score_explosion += 3
    elif ev < 88.5:
        señales.append(f"EV permitida normal-baja {ev:.1f} mph")
        score_explosion += 1

    # Señal 4: BABIP alto (hits cayendo por suerte)
    # No tenemos BABIP en pitcheo pero usamos xwOBA vs wOBA
    xba = s.get('xba', 0)
    if xba < 0.230:
        señales.append(f"xBA permitida muy baja {xba:.3f}")
        score_explosion += 2

    return {
        'Name': nombre,
        'Señales': len(señales),
        'Score_Explosion': score_explosion,
        'Detalle': ' | '.join(señales),
        'ERA': round(era, 2),
        'xERA': round(xera, 2),
        'xwOBA': round(xwoba, 3),
        'EV': round(ev, 1),
        'diff_era': round(diff_era, 2)
    }

# Analizar waivers SP y RP
print("Analizando pitchers en waivers...")
alertas_pit = []
for _, row in pd.concat([waivers_sp, waivers_rp]).iterrows():
    nombre = row['Name']
    stats = pitcheo_2025[pitcheo_2025['Name'] == nombre]
    resultado = analizar_pitcher(nombre, stats)
    if resultado and resultado['Señales'] >= 2:
        alertas_pit.append(resultado)

df_alertas_pit = pd.DataFrame(alertas_pit).sort_values('Score_Explosion', ascending=False) if alertas_pit else pd.DataFrame()

# ================================
# GUARDAR Y MOSTRAR
# ================================
df_alertas_bat.to_csv('data/alertas_explosion_bat.csv', index=False)
df_alertas_pit.to_csv('data/alertas_explosion_pit.csv', index=False)

print("\n" + "=" * 70)
print("🚨 BATEADORES A PUNTO DE EXPLOTAR")
print("=" * 70)
if len(df_alertas_bat) > 0:
    for _, r in df_alertas_bat.head(10).iterrows():
        print(f"  🔥 {r['Name']} — {r['Señales']} señales (score: {r['Score_Explosion']})")
        print(f"     {r['Detalle']}")
else:
    print("  Ninguno detectado")

print("\n" + "=" * 70)
print("🚨 PITCHERS A PUNTO DE EXPLOTAR")
print("=" * 70)
if len(df_alertas_pit) > 0:
    for _, r in df_alertas_pit.head(10).iterrows():
        print(f"  🔥 {r['Name']} — {r['Señales']} señales (score: {r['Score_Explosion']})")
        print(f"     {r['Detalle']}")
else:
    print("  Ninguno detectado")

print(f"\n✅ Guardado en data/alertas_explosion_bat.csv y data/alertas_explosion_pit.csv")