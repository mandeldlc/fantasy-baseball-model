import requests
import os, json
from dotenv import load_dotenv
load_dotenv()

access_token = os.getenv('YAHOO_ACCESS_TOKEN')
headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json'
}

url = "https://fantasysports.yahooapis.com/fantasy/v2/league/469.l.31891/players;status=A;start=0;count=3?format=json"
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2)[:3000])