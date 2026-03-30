import requests
import pandas as pd
import os, sys, json
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import normalizar_nombre

access_token = os.getenv('YAHOO_ACCESS_TOKEN')
headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json'
}

print("Descargando jugadores activos de Yahoo Fantasy...")

todos = []
start = 0
batch = 25

while True:
    url = (
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/469.l.31891/players"
        f";status=A;start={start};count={batch}?format=json"
    )
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  Error {r.status_code}")
        break

    data = r.json()
    players_data = data['fantasy_content']['league'][1]['players']
    count = int(players_data.get('count', 0))

    if count == 0:
        break

    for i in range(count):
        try:
            p_list = players_data[str(i)]['player'][0]
            nombre = None
            posicion = None
            status = 'active'
            ownership = 'freeagent'

            for item in p_list:
                if isinstance(item, dict):
                    if 'name' in item:
                        nombre = item['name'].get('full', '')
                    if 'display_position' in item:
                        posicion = item['display_position']
                    if 'status' in item:
                        status = item['status']

            # Ownership desde player[1]
            try:
                ownership_data = players_data[str(i)]['player'][1]
                if isinstance(ownership_data, dict) and 'ownership' in ownership_data:
                    ownership = ownership_data['ownership'].get('ownership_type', 'freeagent')
            except:
                pass

            if nombre:
                todos.append({
                    'yahoo_name': nombre,
                    'yahoo_norm': normalizar_nombre(nombre),
                    'position': posicion,
                    'status': status if status else 'active',
                    'ownership': ownership
                })
        except Exception as e:
            pass

    print(f"  Batch {start}: {count} jugadores — total: {len(todos)}")
    start += batch
    if count < batch:
        break

df = pd.DataFrame(todos)

# Solo activos — excluir NA, IL, DL, SUSP
df = df[~df['status'].isin(['NA', 'IL', 'IL15', 'IL60', 'DL', 'DL15', 'DL60', 'SUSP'])]
df = df[df['status'].apply(lambda x: str(x) not in ['NA', 'IL', 'IL15', 'IL60'])]

df.to_csv('data/yahoo_players.csv', index=False)
print(f"\n✅ {len(df)} jugadores activos guardados")
print(df['ownership'].value_counts())
print(df['position'].value_counts().head(10))