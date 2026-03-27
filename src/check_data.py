import pandas as pd
bat = pd.read_csv('data/bateo_historico.csv')
pit = pd.read_csv('data/pitcheo_historico.csv')
print(f'Bateadores 2025: {len(bat[bat["year"] == 2025])}')
print(f'Pitchers 2025: {len(pit[pit["year"] == 2025])}')
print(f'Bateadores total: {len(bat)}')
print(f'Pitchers total: {len(pit)}')