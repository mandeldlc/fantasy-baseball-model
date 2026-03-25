import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://baseballsavant.mlb.com/league?season=2025')
soup = BeautifulSoup(r.text, 'html.parser')
tablas = soup.find_all('table')

tabla = tablas[0]
filas = tabla.find_all('tr')

# Ver fila 2 completa (primer equipo)
fila = filas[2]
print("HTML completo fila 2:")
print(fila)