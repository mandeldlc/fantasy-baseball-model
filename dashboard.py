import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import subprocess
import json

load_dotenv()

try:
    if hasattr(st, 'secrets'):
        for key, val in st.secrets.items():
            os.environ[key] = str(val)
except Exception:
    pass

st.set_page_config(
    page_title="Fantasy Baseball Model",
    page_icon="⚾",
    layout="wide"
)

# ================================
# FUNCIONES DE CARGA
# ================================
@st.cache_data(ttl=3600)
def load_roster_from_yahoo():
    try:
        token_data = {
            "access_token": os.getenv('YAHOO_ACCESS_TOKEN', ''),
            "refresh_token": os.getenv('YAHOO_REFRESH_TOKEN', ''),
            "token_type": os.getenv('YAHOO_TOKEN_TYPE', 'bearer'),
            "consumer_key": os.getenv('YAHOO_CLIENT_ID', ''),
            "consumer_secret": os.getenv('YAHOO_CLIENT_SECRET', ''),
            "token_time": float(os.getenv('YAHOO_TOKEN_TIME', '0')),
            "guid": os.getenv('YAHOO_GUID', '')
        }
        query = YahooFantasySportsQuery(
            league_id="31891", game_code="mlb", game_id=469,
            yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
            yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
            yahoo_access_token_json=json.dumps(token_data),
            env_file_location=Path("."), save_token_data_to_env_file=False
        )
        roster = query.get_team_roster_by_week(team_id=6, chosen_week=1)
        jugadores = []
        for player in roster.players:
            jugadores.append({
                'Name': player.name.full,
                'Pos': player.selected_position.position,
                'Team': player.editorial_team_abbr,
                'Status': player.status if player.status else 'active'
            })
        df = pd.DataFrame(jugadores)
        df.to_csv('data/roster.csv', index=False)
        return df
    except Exception as e:
        st.warning(f"Usando roster guardado. Error Yahoo API: {e}")
        return pd.read_csv('data/roster.csv')

@st.cache_data
def load_data():
    bateo = pd.read_csv('data/scoring_bateadores.csv')
    pitcheo = pd.read_csv('data/scoring_pitchers.csv')
    pred_bat = pd.read_csv('data/predicciones_bateadores_2026.csv')
    pred_pit = pd.read_csv('data/predicciones_pitchers_2026.csv')
    return bateo, pitcheo, pred_bat, pred_pit

@st.cache_data(ttl=3600)
def load_proyecciones():
    try:
        return pd.read_csv('data/proyeccion_semanal_bat.csv'), pd.read_csv('data/proyeccion_semanal_pit.csv')
    except:
        return None, None

@st.cache_data(ttl=3600)
def load_waivers():
    try:
        return pd.read_csv('data/waivers_bateadores.csv'), pd.read_csv('data/waivers_sp.csv'), pd.read_csv('data/waivers_rp.csv')
    except:
        return None, None, None

@st.cache_data(ttl=3600)
def load_matchup():
    try:
        with open('data/matchup_semana.json', 'r') as f:
            return json.load(f)
    except:
        return None

@st.cache_data(ttl=3600)
def load_matchup_siguiente():
    try:
        with open('data/matchup_siguiente.json', 'r') as f:
            return json.load(f)
    except:
        return None

@st.cache_data(ttl=3600)
def load_matchup_temporada():
    try:
        with open('data/matchup_temporada.json', 'r') as f:
            return json.load(f)
    except:
        return None

@st.cache_data(ttl=3600)
def load_historial():
    try:
        return pd.read_csv('data/historial_matchups.csv')
    except:
        return None

@st.cache_data(ttl=3600)
def load_streaks():
    try:
        return pd.read_csv('data/streaks_bat.csv'), pd.read_csv('data/streaks_pit.csv')
    except:
        return None, None

@st.cache_data(ttl=3600)
def load_trades():
    try:
        return pd.read_csv('data/trades_sugeridos.csv')
    except:
        return None

@st.cache_data(ttl=3600)
def load_schedule():
    try:
        return pd.read_csv('data/schedule_waivers_sp.csv'), pd.read_csv('data/schedule_roster.csv')
    except:
        return None, None

@st.cache_data(ttl=3600)
def load_alertas():
    try:
        return pd.read_csv('data/alertas_explosion_bat.csv'), pd.read_csv('data/alertas_explosion_pit.csv')
    except:
        return None, None

@st.cache_data(ttl=3600)
def load_closers():
    try:
        return pd.read_csv('data/closers.csv')
    except:
        return None

@st.cache_data(ttl=3600)
def load_favorabilidad():
    try:
        return pd.read_csv('data/favorabilidad_semana.csv')
    except:
        return None

bateo, pitcheo, pred_bat, pred_pit = load_data()

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.header("🏟️ Dando Tabla")
    if st.button("🔄 Actualizar Roster"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔥 Actualizar Waivers"):
        with st.spinner("Analizando agencia libre..."):
            subprocess.run(['python', 'src/waivers.py'])
            st.cache_data.clear()
            st.rerun()
    roster = load_roster_from_yahoo()
    if st.button("⚔️ Actualizar Matchup"):
        with st.spinner("Actualizando matchup..."):
            subprocess.run(['python', 'src/matchup.py'])
            st.cache_data.clear()
            st.rerun()
    st.caption(f"{len(roster)} jugadores")
    st.divider()
    titulares = roster[~roster['Pos'].isin(['BN', 'P'])]
    bench = roster[roster['Pos'].isin(['BN', 'P'])]
    st.markdown("**Titulares**")
    for _, r in titulares.iterrows():
        if r['Status'] in ['DTD', 'DL10', 'DL15', 'DL60', 'NA', 'IL15']:
            st.markdown(f"🔴 **{r['Name']}** — {r['Pos']} ⚠️ {r['Status']}")
        elif r['Status'] == 'active':
            st.markdown(f"🟢 {r['Name']} — {r['Pos']}")
        else:
            st.markdown(f"🟡 {r['Name']} — {r['Pos']} ({r['Status']})")
    st.divider()
    st.markdown("**Bench**")
    for _, r in bench.iterrows():
        if r['Status'] in ['DTD', 'DL10', 'DL15', 'DL60', 'NA', 'IL15']:
            st.markdown(f"🔴 **{r['Name']}** — {r['Pos']} ⚠️ {r['Status']}")
        elif r['Status'] == 'active':
            st.markdown(f"🟢 {r['Name']} — {r['Pos']}")
        else:
            st.markdown(f"🟡 {r['Name']} — {r['Pos']} ({r['Status']})")

# ================================
# HEADER
# ================================
st.title("⚾ Fantasy Baseball Model")
st.caption("Powered by Baseball Savant + ML | Temporada 2026")

col1, col2, col3, col4 = st.columns(4)
with col1:
    top_bat = bateo.iloc[0]
    st.metric("Mejor Bateador", top_bat['Name'], f"Score {top_bat['score']:.0f}")
with col2:
    top_pit = pitcheo.iloc[0]
    st.metric("Mejor Pitcher", top_pit['Name'], f"Score {top_pit['score']:.0f}")
with col3:
    pred_bat['diferencia'] = (pred_bat['woba_pred_2026'] - pred_bat['woba']).round(3)
    subiendo = pred_bat[pred_bat['diferencia'] > 0]
    st.metric("Jugadores al alza", f"{len(subiendo)}", "📈 comprar")
with col4:
    riesgo = pitcheo[pitcheo['score'] < 20]
    st.metric("Pitchers en riesgo", f"{len(riesgo)}", "⚠️ revisar")

lesionados = roster[roster['Status'].isin(['DTD', 'DL10', 'DL15', 'DL60', 'NA', 'IL15'])]
if len(lesionados) > 0:
    with st.expander(f"🚨 {len(lesionados)} jugadores lesionados — click para ver", expanded=True):
        for _, r in lesionados.iterrows():
            st.error(f"**{r['Name']}** ({r['Pos']}) — {r['Status']}")

st.divider()

# ================================
# TABS
# ================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
    "🏏 Bateadores", "⚾ Pitchers", "🔮 Predicciones 2026",
    "⚠️ Alertas", "🔥 Waivers", "📅 Proyección Semanal",
    "⚔️ Matchup", "📊 Historial", "🔥 Streaks", "🔄 Trades",
    "📆 Schedule SP", "💥 Explosión", "🔒 Closers"
])

# TAB 1 - BATEADORES
with tab1:
    st.subheader("Ranking de Bateadores — Semana actual")
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(bateo.sort_values('score'), x='score', y='Name', orientation='h',
                     color='score', color_continuous_scale=['red', 'yellow', 'green'],
                     title='Score semanal por bateador', labels={'score': 'Score (0-100)', 'Name': ''})
        fig.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(bateo[['Name', 'home_run', 'woba', 'xwoba', 'score']].rename(columns={
            'home_run': 'HR', 'woba': 'wOBA', 'xwoba': 'xwOBA', 'score': 'Score'
        }), hide_index=True, height=450)
    st.subheader("wOBA real vs xwOBA esperado")
    fig2 = px.scatter(bateo, x='woba', y='xwoba', text='Name', color='score',
                      color_continuous_scale=['red', 'yellow', 'green'],
                      labels={'woba': 'wOBA 2025', 'xwoba': 'xwOBA 2025'})
    min_val = min(bateo['woba'].min(), bateo['xwoba'].min()) - 0.01
    max_val = max(bateo['woba'].max(), bateo['xwoba'].max()) + 0.01
    fig2.add_shape(type='line', x0=min_val, y0=min_val, x1=max_val, y1=max_val, line=dict(color='gray', dash='dash'))
    fig2.update_traces(textposition='top center')
    fig2.update_layout(height=450)
    st.plotly_chart(fig2, use_container_width=True)

# TAB 2 - PITCHERS
with tab2:
    st.subheader("Ranking de Pitchers — Semana actual")
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(pitcheo.sort_values('score'), x='score', y='Name', orientation='h',
                     color='score', color_continuous_scale=['red', 'yellow', 'green'],
                     title='Score semanal por pitcher', labels={'score': 'Score (0-100)', 'Name': ''})
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(pitcheo[['Name', 'p_era', 'xera', 'p_strikeout', 'p_save', 'score']].rename(columns={
            'p_era': 'ERA', 'xera': 'xERA', 'p_strikeout': 'Ks', 'p_save': 'SV', 'score': 'Score'
        }), hide_index=True, height=400)
    st.subheader("ERA real vs xERA esperado")
    fig3 = px.scatter(pitcheo, x='p_era', y='xera', text='Name', color='score',
                      color_continuous_scale=['green', 'yellow', 'red'],
                      labels={'p_era': 'ERA 2025', 'xera': 'xERA 2025'})
    min_val = min(pitcheo['p_era'].min(), pitcheo['xera'].min()) - 0.1
    max_val = max(pitcheo['p_era'].max(), pitcheo['xera'].max()) + 0.1
    fig3.add_shape(type='line', x0=min_val, y0=min_val, x1=max_val, y1=max_val, line=dict(color='gray', dash='dash'))
    fig3.update_traces(textposition='top center')
    fig3.update_layout(height=450)
    st.plotly_chart(fig3, use_container_width=True)

# TAB 3 - PREDICCIONES
with tab3:
    st.subheader("Predicciones ML para 2026")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Bateadores")
        pred_bat['tendencia'] = pred_bat.apply(lambda r: '📈 Sube' if r['woba_pred_2026'] > r['woba'] else '📉 Baja', axis=1)
        st.dataframe(pred_bat[['Name', 'woba', 'woba_pred_2026', 'diferencia', 'tendencia']].rename(columns={
            'woba': 'wOBA 2025', 'woba_pred_2026': 'wOBA pred 2026', 'diferencia': 'Diff', 'tendencia': 'Tendencia'
        }).sort_values('wOBA pred 2026', ascending=False), hide_index=True, height=450)
    with col2:
        st.markdown("#### Pitchers")
        pred_pit['tendencia'] = pred_pit.apply(lambda r: '📈 Mejora' if r['xera_pred_2026'] < r['xera'] else '📉 Empeora', axis=1)
        pred_pit['diferencia'] = (pred_pit['xera_pred_2026'] - pred_pit['xera']).round(2)
        st.dataframe(pred_pit[['Name', 'xera', 'xera_pred_2026', 'diferencia', 'tendencia']].rename(columns={
            'xera': 'xERA 2025', 'xera_pred_2026': 'xERA pred 2026', 'diferencia': 'Diff', 'tendencia': 'Tendencia'
        }).sort_values('xERA pred 2026', ascending=True), hide_index=True, height=450)

# TAB 4 - ALERTAS
with tab4:
    st.subheader("⚠️ Alertas de la semana")
    col1, col2 = st.columns(2)
    with col1:
        st.success("📈 COMPRAR — Bateadores con upside")
        for _, r in pred_bat[pred_bat['diferencia'] > 0.015].sort_values('diferencia', ascending=False).iterrows():
            st.markdown(f"**{r['Name']}** — xwOBA sugiere +{r['diferencia']:.3f} mejora")
        st.divider()
        st.error("📉 VENDER — Bateadores en declive")
        for _, r in pred_bat[pred_bat['diferencia'] < -0.015].sort_values('diferencia').iterrows():
            st.markdown(f"**{r['Name']}** — proyección baja {r['diferencia']:.3f}")
    with col2:
        st.warning("⚠️ RIESGO — Pitchers con suerte (xERA >> ERA)")
        for _, r in pitcheo[pitcheo['xera'] - pitcheo['p_era'] > 0.50].sort_values('p_era').iterrows():
            diff = r['xera'] - r['p_era']
            st.markdown(f"**{r['Name']}** — ERA {r['p_era']:.2f} pero xERA {r['xera']:.2f} (+{diff:.2f})")
        st.divider()
        st.success("✅ CONFIABLES — Pitchers sólidos")
        for _, r in pitcheo[pitcheo['score'] >= 70].iterrows():
            st.markdown(f"**{r['Name']}** — Score {r['score']:.0f}, ERA {r['p_era']:.2f}")

# TAB 5 - WAIVERS
with tab5:
    st.subheader("🔥 Agentes Libres — Activos disponibles en tu liga")
    waivers_bat, waivers_sp, waivers_rp = load_waivers()
    if waivers_bat is None:
        st.warning("Presiona '🔥 Actualizar Waivers' en el sidebar.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Bateadores libres", len(waivers_bat))
        with col2: st.metric("SP libres", len(waivers_sp))
        with col3: st.metric("RP libres", len(waivers_rp))
        st.divider()
        tab_bat, tab_sp, tab_rp = st.tabs(["🏏 Bateadores", "⚾ SP", "🔥 RP"])
        with tab_bat:
            st.dataframe(waivers_bat[['Name', 'pa', 'home_run', 'woba', 'xwoba', 'diff_xwoba', 'babip', 'exit_velocity_avg', 'breakout_score']].rename(columns={
                'pa': 'PA', 'home_run': 'HR', 'woba': 'wOBA', 'xwoba': 'xwOBA',
                'diff_xwoba': 'xwOBA-wOBA', 'babip': 'BABIP', 'exit_velocity_avg': 'EV', 'breakout_score': 'Score'
            }), hide_index=True, height=600)
        with tab_sp:
            st.dataframe(waivers_sp[['Name', 'p_era', 'xera', 'diff_xera', 'p_strikeout', 'p_win', 'xwoba', 'exit_velocity_avg', 'breakout_score']].rename(columns={
                'p_era': 'ERA', 'xera': 'xERA', 'diff_xera': 'ERA-xERA',
                'p_strikeout': 'Ks', 'p_win': 'W', 'xwoba': 'xwOBA', 'exit_velocity_avg': 'EV', 'breakout_score': 'Score'
            }), hide_index=True, height=600)
        with tab_rp:
            st.dataframe(waivers_rp[['Name', 'p_era', 'xera', 'diff_xera', 'p_strikeout', 'p_save', 'xwoba', 'exit_velocity_avg', 'breakout_score']].rename(columns={
                'p_era': 'ERA', 'xera': 'xERA', 'diff_xera': 'ERA-xERA',
                'p_strikeout': 'Ks', 'p_save': 'SV', 'xwoba': 'xwOBA', 'exit_velocity_avg': 'EV', 'breakout_score': 'Score'
            }), hide_index=True, height=600)
        st.divider()
        st.subheader("⚡ Agarra ahora")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🏏 Bateadores")
            for _, r in waivers_bat[waivers_bat['diff_xwoba'] > 0.020].head(5).iterrows():
                st.markdown(f"**{r['Name']}** — xwOBA +{r['diff_xwoba']:.3f}")
        with col2:
            st.success("⚾ SP")
            for _, r in waivers_sp[waivers_sp['diff_xera'] > 1.0].head(5).iterrows():
                st.markdown(f"**{r['Name']}** — ERA {r['p_era']:.2f} xERA {r['xera']:.2f}")
        with col3:
            st.success("🔥 RP")
            for _, r in waivers_rp[waivers_rp['diff_xera'] > 1.0].head(5).iterrows():
                st.markdown(f"**{r['Name']}** — ERA {r['p_era']:.2f} xERA {r['xera']:.2f} SV:{r['p_save']:.0f}")

# TAB 6 - PROYECCIÓN SEMANAL
with tab6:
    st.subheader("📅 Proyección Semanal — Próximos 7 días")
    proy_bat, proy_pit = load_proyecciones()
    if proy_bat is None:
        st.warning("Corre primero: python src/modelo_avanzado.py")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏏 Bateadores")
            proy_bat['tendencia'] = proy_bat.apply(lambda r: '📈' if r['fantasy_score_proyectado'] > r['fantasy_score_actual'] else '📉', axis=1)
            proy_bat['diff'] = (proy_bat['fantasy_score_proyectado'] - proy_bat['fantasy_score_actual']).round(1)
            fig_p = px.bar(proy_bat.sort_values('fantasy_score_proyectado'), x='fantasy_score_proyectado', y='Name', orientation='h',
                           color='diff', color_continuous_scale=['red', 'yellow', 'green'])
            fig_p.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(proy_bat[['Name', 'fantasy_score_actual', 'fantasy_score_proyectado', 'diff', 'tendencia']].sort_values('fantasy_score_proyectado', ascending=False).rename(columns={
                'fantasy_score_actual': 'Score actual', 'fantasy_score_proyectado': 'Score 7 días', 'diff': 'Diferencia', 'tendencia': 'Tendencia'
            }), hide_index=True, height=400)
        with col2:
            st.markdown("#### ⚾ Pitchers")
            proy_pit['tendencia'] = proy_pit.apply(lambda r: '📈' if r['fantasy_score_proyectado'] > r['fantasy_score_actual'] else '📉', axis=1)
            proy_pit['diff'] = (proy_pit['fantasy_score_proyectado'] - proy_pit['fantasy_score_actual']).round(1)
            fig_pp = px.bar(proy_pit.sort_values('fantasy_score_proyectado'), x='fantasy_score_proyectado', y='Name', orientation='h',
                            color='diff', color_continuous_scale=['red', 'yellow', 'green'])
            fig_pp.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_pp, use_container_width=True)
            st.dataframe(proy_pit[['Name', 'fantasy_score_actual', 'fantasy_score_proyectado', 'diff', 'tendencia']].sort_values('fantasy_score_proyectado', ascending=False).rename(columns={
                'fantasy_score_actual': 'Score actual', 'fantasy_score_proyectado': 'Score 7 días', 'diff': 'Diferencia', 'tendencia': 'Tendencia'
            }), hide_index=True, height=400)

# TAB 7 - MATCHUP
with tab7:
    matchup = load_matchup()
    matchup_sig = load_matchup_siguiente()
    todas_semanas = load_matchup_temporada()

    def render_matchup(m):
        st.caption(f"📅 {m['week_start']} — {m['week_end']}")
        prob_ganar = m.get('prob_ganar', 50)
        prob_perder = m.get('prob_perder', 50)
        odds_ganar = m.get('odds_ganar', '+100')
        odds_perder = m.get('odds_perder', '+100')
        st.markdown(f"""
        <div style='border-radius: 12px; padding: 16px; margin: 10px 0; border: 1px solid #333'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 8px'>
                <span style='font-weight: 700; font-size: 15px'>🏟️ Dando Tabla &nbsp;<span style='color: #1D9E75; font-size: 13px'>{odds_ganar}</span></span>
                <span style='font-weight: 700; font-size: 15px'><span style='color: #E24B4A; font-size: 13px'>{odds_perder}</span>&nbsp; {m['oponente']} 🏟️</span>
            </div>
            <div style='display: flex; border-radius: 8px; overflow: hidden; height: 32px'>
                <div style='width: {prob_ganar}%; background: #1D9E75; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px'>{prob_ganar}%</div>
                <div style='width: {prob_perder}%; background: #E24B4A; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px'>{prob_perder}%</div>
            </div>
            <div style='text-align: center; margin-top: 10px; font-size: 13px; opacity: 0.7'>
                {'🏆 Favorito esta semana' if prob_ganar >= 50 else '⚠️ Underdog esta semana'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        mis_bat = m['mis_bat']
        opp_bat = m['opp_bat']
        mis_pit = m['mis_pit']
        opp_pit = m['opp_pit']
        col1, col2, col3 = st.columns(3)
        with col1:
            ventajas_bat = sum(1 for s in ['HR_avg', 'OPS', 'wOBA', 'xwOBA', 'Barrel%'] if mis_bat.get(s, 0) > opp_bat.get(s, 0))
            st.metric("Ventajas en bateo", f"{ventajas_bat}/5", "✅ Superior" if ventajas_bat >= 3 else "⚠️ Revisar")
        with col2:
            ventajas_pit = sum(1 for s in ['ERA', 'xERA', 'Ks', 'xwOBA'] if (mis_pit.get(s, 0) < opp_pit.get(s, 0) if s in ['ERA', 'xERA', 'xwOBA'] else mis_pit.get(s, 0) > opp_pit.get(s, 0)))
            st.metric("Ventajas en pitcheo", f"{ventajas_pit}/4", "✅ Superior" if ventajas_pit >= 2 else "⚠️ Revisar")
        with col3:
            total_v = ventajas_bat + ventajas_pit
            st.metric("Ventaja total", f"{total_v}/9", "🏆 Favorito" if total_v >= 5 else "⚠️ Parejo")
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏏 Comparativo Bateadores")
            bat_data = [{'Stat': s, 'Dando Tabla': mis_bat.get(s, 0), m['oponente']: opp_bat.get(s, 0),
                         'Ventaja': "✅ Tú" if mis_bat.get(s, 0) > opp_bat.get(s, 0) else "❌ Ellos"}
                        for s in ['HR_avg', 'OPS', 'wOBA', 'xwOBA', 'EV', 'Barrel%']]
            st.dataframe(pd.DataFrame(bat_data), hide_index=True, height=250)
        with col2:
            st.markdown("#### ⚾ Comparativo Pitchers")
            pit_data = []
            for s in ['ERA', 'xERA', 'Ks', 'xwOBA', 'EV_against']:
                mi_val = mis_pit.get(s, 0)
                opp_val = opp_pit.get(s, 0)
                if s in ['ERA', 'xERA', 'xwOBA', 'EV_against']:
                    ventaja = "✅ Tú" if mi_val < opp_val else "❌ Ellos"
                else:
                    ventaja = "✅ Tú" if mi_val > opp_val else "❌ Ellos"
                pit_data.append({'Stat': s, 'Dando Tabla': mi_val, m['oponente']: opp_val, 'Ventaja': ventaja})
            st.dataframe(pd.DataFrame(pit_data), hide_index=True, height=220)
        st.divider()
        st.subheader("⚡ Recomendaciones")
        if ventajas_bat >= 3:
            st.success("✅ Tu lineup de bateadores es superior — arranca todos tus titulares")
        else:
            st.warning("⚠️ Tu bateo está débil — revisa waivers para reforzar")
        if ventajas_pit >= 2:
            st.success("✅ Tu pitcheo tiene ventaja — mantén tus SP titulares")
        else:
            st.warning("⚠️ Tu pitcheo está en desventaja — busca SP en waivers")

    if matchup is None:
        st.warning("Corre primero: python src/matchup.py")
    else:
        # Construir labels de todos los tabs
        label_actual = f"⚔️ Sem {matchup['semana']} — vs {matchup['oponente']}"
        label_siguiente = f"🔭 Sem {matchup_sig['semana'] if matchup_sig else '?'} — vs {matchup_sig['oponente'] if matchup_sig else '?'}"

        if todas_semanas:
            labels_temporada = []
            for s in todas_semanas:
                p = s['prob_ganar']
                ic = "🟢" if p > 55 else "🔴" if p < 45 else "🟡"
                labels_temporada.append(f"Sem {s['semana']} {ic} vs {s['oponente'][:15]}")
            todos_labels = [label_actual, label_siguiente] + labels_temporada
        else:
            todos_labels = [label_actual, label_siguiente]

        todos_tabs = st.tabs(todos_labels)

        with todos_tabs[0]:
            render_matchup(matchup)

        with todos_tabs[1]:
            if matchup_sig:
                render_matchup(matchup_sig)
            else:
                st.warning("No hay matchup disponible.")

        if todas_semanas:
            for i, m in enumerate(todas_semanas):
                with todos_tabs[i + 2]:
                    render_matchup(m)

# TAB 8 - HISTORIAL
with tab8:
    st.subheader("📊 Historial de Matchups — Temporada 2026")
    historial = load_historial()
    if historial is None or len(historial) == 0:
        st.info("La temporada empieza el 25 de marzo — el historial se actualizará automáticamente cada semana.")
    else:
        wins = len(historial[historial['resultado'] == 'W'])
        losses = len(historial[historial['resultado'] == 'L'])
        ties = len(historial[historial['resultado'] == 'T'])
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Victorias", wins, "✅")
        with col2: st.metric("Derrotas", losses, "❌")
        with col3: st.metric("Empates", ties, "➡️")
        with col4:
            pct = round(wins / len(historial) * 100, 1) if len(historial) > 0 else 0
            st.metric("Win %", f"{pct}%")
        st.divider()
        st.dataframe(historial[['semana', 'week_start', 'oponente', 'mis_puntos', 'opp_puntos', 'resultado']].rename(columns={
            'semana': 'Semana', 'week_start': 'Inicio', 'oponente': 'Oponente',
            'mis_puntos': 'Mis Pts', 'opp_puntos': 'Opp Pts', 'resultado': 'Resultado'
        }), hide_index=True, height=400)

# TAB 9 - STREAKS
with tab9:
    st.subheader("🔥 Hot / Cold Streaks")
    streaks_bat, streaks_pit = load_streaks()
    if streaks_bat is None:
        st.warning("Corre primero: python src/streaks.py")
    else:
        filtro = st.radio("Mostrar:", ["Todo", "Mi Roster", "Waiver"], horizontal=True)
        if filtro != "Todo":
            streaks_bat = streaks_bat[streaks_bat['Fuente'] == filtro]
            streaks_pit = streaks_pit[streaks_pit['Fuente'] == filtro]
        tab_bat, tab_pit = st.tabs(["🏏 Bateadores", "⚾ Pitchers"])
        with tab_bat:
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("🔥 HOT", len(streaks_bat[streaks_bat['Streak'] == '🔥 HOT']))
            with col2: st.metric("🥶 COLD", len(streaks_bat[streaks_bat['Streak'] == '🥶 COLD']))
            with col3: st.metric("➡️ Neutral", len(streaks_bat[streaks_bat['Streak'] == '➡️ NEUTRAL']))
            st.divider()
            streak_filter = st.selectbox("Filtrar:", ["Todos", "🔥 HOT", "🥶 COLD", "➡️ NEUTRAL"], key="bat_streak")
            mostrar_bat = streaks_bat[streaks_bat['Streak'] == streak_filter] if streak_filter != "Todos" else streaks_bat
            cols_bat = [c for c in mostrar_bat.columns if c in ['Name', 'Fuente', 'Diff', 'Streak', 'EV', 'Barrel%'] or 'wOBA' in c or 'xwOBA' in c]
            st.dataframe(mostrar_bat[cols_bat], hide_index=True, height=500)
        with tab_pit:
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("🔥 HOT", len(streaks_pit[streaks_pit['Streak'] == '🔥 HOT']))
            with col2: st.metric("🥶 COLD", len(streaks_pit[streaks_pit['Streak'] == '🥶 COLD']))
            with col3: st.metric("➡️ Neutral", len(streaks_pit[streaks_pit['Streak'] == '➡️ NEUTRAL']))
            st.divider()
            streak_filter_p = st.selectbox("Filtrar:", ["Todos", "🔥 HOT", "🥶 COLD", "➡️ NEUTRAL"], key="pit_streak")
            mostrar_pit = streaks_pit[streaks_pit['Streak'] == streak_filter_p] if streak_filter_p != "Todos" else streaks_pit
            cols_pit = [c for c in mostrar_pit.columns if c in ['Name', 'Fuente', 'Ks', 'Diff ERA', 'Streak'] or 'ERA' in c or 'xERA' in c]
            st.dataframe(mostrar_pit[cols_pit], hide_index=True, height=500)

# TAB 10 - TRADES
with tab10:
    st.subheader("🔄 Sugerencias de Trades")
    trades = load_trades()
    if trades is None or len(trades) == 0:
        st.info("Corre primero: python src/trades.py")
    else:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Trades sugeridos", len(trades))
        with col2: st.metric("Equipos con oportunidades", trades['oponente'].nunique())
        with col3: st.metric("Categorías a mejorar", trades['categoria_pedir'].nunique())
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            equipo_sel = st.selectbox("Filtrar por equipo:", ["Todos"] + trades['oponente'].unique().tolist())
        with col2:
            cat_sel = st.selectbox("Filtrar por categoría:", ["Todas"] + trades['categoria_pedir'].unique().tolist())
        df_filtrado = trades.copy()
        if equipo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['oponente'] == equipo_sel]
        if cat_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado['categoria_pedir'] == cat_sel]
        st.divider()
        for _, r in df_filtrado.head(20).iterrows():
            tipo_icon = "🏏" if r['tipo'] == 'Bateador' else "⚾"
            valor_pedir = r['valor_pedir'] if pd.notna(r['valor_pedir']) else 'N/A'
            mi_debilidad = r['mi_debilidad'] if pd.notna(r['mi_debilidad']) else 'N/A'
            fortalezas = r['mis_fortalezas'] if pd.notna(r['mis_fortalezas']) else 'N/A'
            st.markdown(f"""
            **{tipo_icon} Pide: {r['pedir']}** de *{r['oponente']}*
            - Categoría que mejoras: **{r['categoria_pedir']}** — ellos tienen `{valor_pedir}` vs tú `{mi_debilidad}`
            - Tus fortalezas para ofrecer: `{fortalezas}`
            ---
            """)

# TAB 11 - SCHEDULE SP
with tab11:
    st.subheader("📆 Schedule SP — Starts y Favorabilidad")
    sched_waivers, sched_roster = load_schedule()
    fav_modelo = load_favorabilidad()

    def get_fav_modelo(nombre, oponentes_str):
        if fav_modelo is None or len(fav_modelo) == 0:
            return None
        try:
            opp = oponentes_str.split('vs ')[1].split(' (')[0].strip()
            match = fav_modelo[(fav_modelo['Name'] == nombre) & (fav_modelo['Oponente'] == opp)]
            if len(match) > 0:
                return match.iloc[0]
        except:
            pass
        return None

    if sched_waivers is None:
        st.warning("Corre primero: python src/schedule.py")
    else:
        st.markdown("#### 📋 Mis Pitchers esta semana")
        mis_pit = sched_roster[sched_roster['Pos'].isin(['SP', 'RP', 'P'])]
        for _, r in mis_pit.iterrows():
            fav = get_fav_modelo(r['Name'], r.get('Oponentes', ''))
            if r['Starts'] >= 2:
                st.success(f"⭐ **{r['Name']}** ({r['Pos']}) — {r['Doble_Start']} | Fav: {r['Favorabilidad']} | {r['Oponentes']}")
            elif r['Starts'] == 1:
                if fav is not None:
                    st.info(f"➡️ **{r['Name']}** ({r['Pos']}) — {fav['Clasificacion']} | xwOBA: {fav['xwOBA_pred']:.3f} | Prob: {fav['Prob_favorable']:.0f}% | {r['Oponentes']}")
                else:
                    st.info(f"➡️ **{r['Name']}** ({r['Pos']}) — {r['Doble_Start']} | Fav: {r['Favorabilidad']} | {r['Oponentes']}")
            else:
                st.error(f"❌ **{r['Name']}** ({r['Pos']}) — Sin start esta semana")
        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.metric("SP doble start en waivers", len(sched_waivers[sched_waivers['Starts'] >= 2]))
        with col2: st.metric("SP simple start en waivers", len(sched_waivers[sched_waivers['Starts'] == 1]))
        st.divider()
        tab_doble, tab_simple, tab_ml = st.tabs(["⭐ Doble Start", "➡️ Simple Start", "🤖 Modelo ML"])
        with tab_doble:
            dobles_df = sched_waivers[sched_waivers['Starts'] >= 2]
            if len(dobles_df) == 0:
                st.info("No hay doble starts anunciados aún")
            else:
                st.dataframe(dobles_df[['Name', 'Doble_Start', 'Favorabilidad', 'ERA', 'xERA', 'Breakout_Score', 'Oponentes']], hide_index=True, height=400)
        with tab_simple:
            st.dataframe(sched_waivers[sched_waivers['Starts'] == 1].head(20)[['Name', 'Favorabilidad', 'ERA', 'xERA', 'Breakout_Score', 'Oponentes']], hide_index=True, height=400)
        with tab_ml:
            st.caption("Favorabilidad basada en historial Statcast 2022-2025 + modelo ML (96.6% accuracy)")
            if fav_modelo is not None and len(fav_modelo) > 0:
                st.dataframe(fav_modelo[['Name', 'Oponente', 'xwOBA_pred', 'Prob_favorable', 'Clasificacion', 'PA_hist', 'xwOBA_hist', 'Fuente_pred']].rename(columns={
                    'xwOBA_pred': 'xwOBA Pred', 'Prob_favorable': 'Prob%',
                    'PA_hist': 'PA Hist', 'xwOBA_hist': 'xwOBA Hist', 'Fuente_pred': 'Fuente'
                }), hide_index=True, height=500)
            else:
                st.info("Corre primero: python src/modelo_favorabilidad.py")

# TAB 12 - ALERTAS EXPLOSION
with tab12:
    st.subheader("💥 Jugadores a Punto de Explotar")
    alertas_bat, alertas_pit = load_alertas()
    if alertas_bat is None:
        st.warning("Corre primero: python src/alertas_explosion.py")
    else:
        col1, col2 = st.columns(2)
        with col1: st.metric("🏏 Bateadores detectados", len(alertas_bat))
        with col2: st.metric("⚾ Pitchers detectados", len(alertas_pit))
        st.divider()
        tab_bat, tab_pit = st.tabs(["🏏 Bateadores", "⚾ Pitchers"])
        with tab_bat:
            if len(alertas_bat) == 0:
                st.info("No hay bateadores detectados")
            else:
                for _, r in alertas_bat.head(15).iterrows():
                    with st.expander(f"🔥 **{r['Name']}** — {r['Señales']} señales (Score: {r['Score_Explosion']})"):
                        st.markdown(f"**Señales:** {r['Detalle']}")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1: st.metric("wOBA", r['wOBA'])
                        with col2: st.metric("xwOBA", r['xwOBA'])
                        with col3: st.metric("BABIP", r['BABIP'])
                        with col4: st.metric("EV", r['EV'])
        with tab_pit:
            if len(alertas_pit) == 0:
                st.info("No hay pitchers detectados")
            else:
                for _, r in alertas_pit.head(15).iterrows():
                    with st.expander(f"🔥 **{r['Name']}** — {r['Señales']} señales (Score: {r['Score_Explosion']})"):
                        st.markdown(f"**Señales:** {r['Detalle']}")
                        col1, col2, col3 = st.columns(3)
                        with col1: st.metric("ERA", r['ERA'])
                        with col2: st.metric("xERA", r['xERA'])
                        with col3: st.metric("EV permitida", r['EV'])

# TAB 13 - CLOSERS
with tab13:
    st.subheader("🔒 Closers Confirmados en Waivers")
    closers = load_closers()
    if closers is None or len(closers) == 0:
        st.warning("Corre primero: python src/closers.py")
    else:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("🔒 Closers élite", len(closers[closers['SV_2025'] >= 20]), "20+ SV 2025")
        with col2: st.metric("✅ Closers confirmados", len(closers[closers['SV_2025'] >= 10]), "10+ SV 2025")
        with col3: st.metric("👀 Con oportunidades", len(closers[closers['SV_2025'] >= 3]), "3+ SV 2025")
        st.divider()
        st.dataframe(closers[['Name', 'SV_2025', 'SV_2024', 'ERA', 'xERA', 'xwOBA', 'Closer_Score', 'Tipo']].rename(columns={
            'SV_2025': 'SV 25', 'SV_2024': 'SV 24', 'Closer_Score': 'Score', 'Tipo': 'Detalle'
        }), hide_index=True, height=500)
        st.divider()
        st.subheader("⚡ Agarra ahora")
        for _, r in closers[closers['SV_2025'] >= 10].head(5).iterrows():
            st.success(f"🔒 **{r['Name']}** — {r['SV_2025']:.0f} SV 2025 | ERA {r['ERA']:.2f} | xERA {r['xERA']:.2f}")