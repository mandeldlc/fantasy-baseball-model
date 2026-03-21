import pandas as pd

roster = [
    {"Name": "Salvador Perez",    "Team": "KC",  "Pos": "C",    "Status": "starter"},
    {"Name": "Josh Naylor",       "Team": "SEA", "Pos": "1B",   "Status": "starter"},
    {"Name": "Nico Hoerner",      "Team": "CHC", "Pos": "2B",   "Status": "starter"},
    {"Name": "Junior Caminero",   "Team": "TB",  "Pos": "3B",   "Status": "starter"},
    {"Name": "Zach Neto",         "Team": "LAA", "Pos": "SS",   "Status": "starter"},
    {"Name": "Kyle Tucker",       "Team": "LAD", "Pos": "OF",   "Status": "starter"},
    {"Name": "Jarren Duran",      "Team": "BOS", "Pos": "OF",   "Status": "starter"},
    {"Name": "Riley Greene",      "Team": "DET", "Pos": "OF",   "Status": "starter"},
    {"Name": "Bo Bichette",       "Team": "NYM", "Pos": "UTIL", "Status": "starter"},
    {"Name": "Michael Harris II", "Team": "ATL", "Pos": "UTIL", "Status": "starter"},
    {"Name": "Johnathan Wilson",  "Team": "ATH", "Pos": "SS",   "Status": "bench"},
    {"Name": "Dylan Crews",       "Team": "WSH", "Pos": "OF",   "Status": "bench"},
    {"Name": "Heliot Ramos",      "Team": "SF",  "Pos": "OF",   "Status": "bench"},
    {"Name": "Otto Lopez",        "Team": "MIA", "Pos": "2B",   "Status": "bench"},
    {"Name": "Logan Gilbert",     "Team": "SEA", "Pos": "SP",   "Status": "starter"},
    {"Name": "Luis Castillo",     "Team": "SEA", "Pos": "SP",   "Status": "starter"},
    {"Name": "Ryne Nelson",       "Team": "AZ",  "Pos": "RP",   "Status": "starter"},
    {"Name": "Dennis Santana",    "Team": "PIT", "Pos": "RP",   "Status": "starter"},
    {"Name": "Trey Yesavage",     "Team": "TOR", "Pos": "SP",   "Status": "bench"},
    {"Name": "Andrew Abbott",     "Team": "CIN", "Pos": "SP",   "Status": "bench"},
    {"Name": "Carlos Rodón",      "Team": "NYY", "Pos": "SP",   "Status": "bench"},
    {"Name": "Shane Bieber",      "Team": "TOR", "Pos": "SP",   "Status": "bench"},
]

df_roster = pd.DataFrame(roster)
df_roster.to_csv('data/roster.csv', index=False)

# Cargar datos
bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

# Arreglar nombres
bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_2025 = bateo[bateo['year'] == 2025].copy()
pitcheo_2025 = pitcheo[pitcheo['year'] == 2025].copy()

mis_bateadores = df_roster[~df_roster['Pos'].isin(['SP', 'RP'])]['Name'].tolist()
mis_pitchers = df_roster[df_roster['Pos'].isin(['SP', 'RP'])]['Name'].tolist()

print("=" * 60)
print("TUS BATEADORES - Stats 2025")
print("=" * 60)
resultado_bat = bateo_2025[bateo_2025['Name'].isin(mis_bateadores)][[
    'Name', 'pa', 'home_run', 'on_base_plus_slg', 
    'woba', 'xwoba', 'xba', 'xslg', 'babip',
    'exit_velocity_avg', 'barrel_batted_rate'
]].sort_values('woba', ascending=False)
print(resultado_bat.to_string(index=False))

print("\n" + "=" * 60)
print("TUS PITCHERS - Stats 2025")
print("=" * 60)
resultado_pit = pitcheo_2025[pitcheo_2025['Name'].isin(mis_pitchers)][[
    'Name', 'p_era', 'xera', 'p_strikeout', 
    'p_win', 'p_save', 'xwoba', 'exit_velocity_avg'
]].sort_values('p_era', ascending=True)
print(resultado_pit.to_string(index=False))

# Guardar resultados
resultado_bat.to_csv('data/mis_bateadores_2025.csv', index=False)
resultado_pit.to_csv('data/mis_pitchers_2025.csv', index=False)
print("\n✅ Archivos guardados en data/")