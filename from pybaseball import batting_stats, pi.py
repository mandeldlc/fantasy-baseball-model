import statsapi
import pandas as pd

# Descargar roster de equipos y stats
print("Descargando datos MLB 2026...")

# Stats de bateadores
batting = statsapi.get('stats', {
    'stats': 'season',
    'group': 'hitting',
    'season': 2026,
    'limit': 300,
    'offset': 0
})

jugadores = []
for p in batting['stats'][0]['splits']:
    s = p['stat']
    jugadores.append({
        'Name': p['player']['fullName'],
        'Team': p.get('team', {}).get('name', 'N/A'),
        'G': s.get('gamesPlayed', 0),
        'R': s.get('runs', 0),
        'HR': s.get('homeRuns', 0),
        'RBI': s.get('rbi', 0),
        'SB': s.get('stolenBases', 0),
        'OBP': s.get('obp', 0),
        'SLG': s.get('slg', 0),
    })

bateo = pd.DataFrame(jugadores)
bateo.to_csv('data/bateo_2026.csv', index=False)

print(f"✅ Bateadores: {len(bateo)}")
print("\n--- TOP 5 HR ---")
print(bateo.sort_values('HR', ascending=False).head())