import pandas as pd

bateo = pd.read_csv('data/bateo_historico.csv')

# Ver qué columnas tienen datos reales
print("Columnas con datos:")
for col in bateo.columns:
    no_nulos = bateo[col].notna().sum()
    if no_nulos > 0:
        print(f"  {col}: {no_nulos} valores")