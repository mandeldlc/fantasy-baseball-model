from datetime import date

def get_blend_weights():
    """Retorna (peso_historico, peso_2026) según el mes actual"""
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

def get_season():
    return date.today().year

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

def blend_stat(val_hist, val_curr, pa_curr, pa_threshold=50):
    """Blend inteligente: más peso a 2026 cuando hay más data"""
    w_hist, w_curr = get_blend_weights()
    if pa_curr >= pa_threshold:
        # Suficiente data 2026 — usar pesos normales
        return round(w_hist * val_hist + w_curr * val_curr, 3)
    elif pa_curr > 0:
        # Poca data 2026 — más peso al historial
        factor = pa_curr / pa_threshold
        w_curr_adj = w_curr * factor
        w_hist_adj = 1 - w_curr_adj
        return round(w_hist_adj * val_hist + w_curr_adj * val_curr, 3)
    else:
        return val_hist