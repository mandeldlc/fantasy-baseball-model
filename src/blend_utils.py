from datetime import date

def get_season():
    return date.today().year

def get_blend_weights():
    """Retorna (peso_historico, peso_actual) según el mes actual"""
    mes = date.today().month
    if mes <= 4:
        return 0.90, 0.10
    elif mes <= 5:
        return 0.70, 0.30
    elif mes <= 6:
        return 0.50, 0.50
    elif mes <= 7:
        return 0.30, 0.70
    else:
        return 0.10, 0.90

def get_last_seasons(n=3):
    """Retorna las últimas N temporadas — automático para cualquier año"""
    season = get_season()
    return list(range(season - n, season + 1))  # ej: 2027 → [2024, 2025, 2026, 2027]

def get_min_pa():
    mes = date.today().month
    if mes <= 4: return 5
    elif mes <= 5: return 20
    else: return 50

def get_min_ip():
    mes = date.today().month
    if mes <= 4: return 1
    elif mes <= 5: return 5
    else: return 20

def get_curr_data(df, min_registros=50):
    """
    Retorna datos de la temporada actual con fallback al año anterior.
    Si hay pocos datos del año actual, usa el anterior.
    """
    season = get_season()
    curr = df[df['year'] == season]
    if len(curr) >= min_registros:
        return curr.copy()
    return df[df['year'] == season - 1].copy()

def get_season_data(df, years=None):
    """
    Retorna datos de las últimas temporadas para entrenar modelos.
    Por defecto usa las últimas 3 temporadas completas (excluye la actual).
    """
    season = get_season()
    if years is None:
        years = [season - 3, season - 2, season - 1]
    return df[df['year'].isin(years)].copy()

def blend_stat(val_hist, val_curr, pa_curr, pa_threshold=50):
    """Blend inteligente: más peso a actual cuando hay más data"""
    w_hist, w_curr = get_blend_weights()
    if pa_curr >= pa_threshold:
        return round(w_hist * val_hist + w_curr * val_curr, 3)
    elif pa_curr > 0:
        factor = pa_curr / pa_threshold
        w_curr_adj = w_curr * factor
        w_hist_adj = 1 - w_curr_adj
        return round(w_hist_adj * val_hist + w_curr_adj * val_curr, 3)
    else:
        return val_hist