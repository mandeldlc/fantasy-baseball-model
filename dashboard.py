import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Fantasy Baseball Model",
    page_icon="⚾",
    layout="wide"
)

# ================================
# CARGAR DATOS
# ================================
@st.cache_data
def load_data():
    bateo = pd.read_csv('data/scoring_bateadores.csv')
    pitcheo = pd.read_csv('data/scoring_pitchers.csv')
    pred_bat = pd.read_csv('data/predicciones_bateadores_2026.csv')
    pred_pit = pd.read_csv('data/predicciones_pitchers_2026.csv')
    return bateo, pitcheo, pred_bat, pred_pit

bateo, pitcheo, pred_bat, pred_pit = load_data()

# ================================
# HEADER
# ================================
st.title("⚾ Fantasy Baseball Model")
st.caption("Powered by Baseball Savant + ML | Temporada 2026")

# ================================
# MÉTRICAS RESUMEN
# ================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    top_bat = bateo.iloc[0]
    st.metric("Mejor Bateador", top_bat['Name'], f"Score {top_bat['score']:.0f}")
with col2:
    top_pit = pitcheo.iloc[0]
    st.metric("Mejor Pitcher", top_pit['Name'], f"Score {top_pit['score']:.0f}")
with col3:
    subiendo = pred_bat[pred_bat['woba_pred_2026'] > pred_bat['woba']]
    st.metric("Jugadores al alza", f"{len(subiendo)}", "📈 comprar")
with col4:
    riesgo = pitcheo[pitcheo['score'] < 20]
    st.metric("Pitchers en riesgo", f"{len(riesgo)}", "⚠️ revisar")

st.divider()

# ================================
# TABS
# ================================
tab1, tab2, tab3, tab4 = st.tabs(["🏏 Bateadores", "⚾ Pitchers", "🔮 Predicciones 2026", "⚠️ Alertas"])

# TAB 1 - BATEADORES
with tab1:
    st.subheader("Ranking de Bateadores — Semana actual")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            bateo.sort_values('score'),
            x='score',
            y='Name',
            orientation='h',
            color='score',
            color_continuous_scale=['red', 'yellow', 'green'],
            title='Score semanal por bateador',
            labels={'score': 'Score (0-100)', 'Name': ''}
        )
        fig.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            bateo[['Name', 'home_run', 'woba', 'xwoba', 'score']].rename(columns={
                'home_run': 'HR',
                'woba': 'wOBA',
                'xwoba': 'xwOBA',
                'score': 'Score'
            }),
            hide_index=True,
            height=450
        )

    # Scatter woba vs xwoba
    st.subheader("wOBA real vs xwOBA esperado")
    st.caption("Jugadores arriba de la línea van a mejorar. Abajo van a bajar.")
    fig2 = px.scatter(
        bateo,
        x='woba',
        y='xwoba',
        text='Name',
        color='score',
        color_continuous_scale=['red', 'yellow', 'green'],
        labels={'woba': 'wOBA 2025', 'xwoba': 'xwOBA 2025'}
    )
    min_val = min(bateo['woba'].min(), bateo['xwoba'].min()) - 0.01
    max_val = max(bateo['woba'].max(), bateo['xwoba'].max()) + 0.01
    fig2.add_shape(type='line', x0=min_val, y0=min_val, x1=max_val, y1=max_val,
                   line=dict(color='gray', dash='dash'))
    fig2.update_traces(textposition='top center')
    fig2.update_layout(height=450)
    st.plotly_chart(fig2, use_container_width=True)

# TAB 2 - PITCHERS
with tab2:
    st.subheader("Ranking de Pitchers — Semana actual")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            pitcheo.sort_values('score'),
            x='score',
            y='Name',
            orientation='h',
            color='score',
            color_continuous_scale=['red', 'yellow', 'green'],
            title='Score semanal por pitcher',
            labels={'score': 'Score (0-100)', 'Name': ''}
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            pitcheo[['Name', 'p_era', 'xera', 'p_strikeout', 'p_save', 'score']].rename(columns={
                'p_era': 'ERA',
                'xera': 'xERA',
                'p_strikeout': 'Ks',
                'p_save': 'SV',
                'score': 'Score'
            }),
            hide_index=True,
            height=400
        )

    # ERA vs xERA
    st.subheader("ERA real vs xERA esperado")
    st.caption("Pitchers arriba de la línea tienen suerte — van a empeorar.")
    fig3 = px.scatter(
        pitcheo,
        x='p_era',
        y='xera',
        text='Name',
        color='score',
        color_continuous_scale=['green', 'yellow', 'red'],
        labels={'p_era': 'ERA 2025', 'xera': 'xERA 2025'}
    )
    min_val = min(pitcheo['p_era'].min(), pitcheo['xera'].min()) - 0.1
    max_val = max(pitcheo['p_era'].max(), pitcheo['xera'].max()) + 0.1
    fig3.add_shape(type='line', x0=min_val, y0=min_val, x1=max_val, y1=max_val,
                   line=dict(color='gray', dash='dash'))
    fig3.update_traces(textposition='top center')
    fig3.update_layout(height=450)
    st.plotly_chart(fig3, use_container_width=True)

# TAB 3 - PREDICCIONES
with tab3:
    st.subheader("Predicciones ML para 2026")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Bateadores")
        pred_bat['tendencia'] = pred_bat.apply(
            lambda r: '📈 Sube' if r['woba_pred_2026'] > r['woba'] else '📉 Baja', axis=1
        )
        pred_bat['diferencia'] = (pred_bat['woba_pred_2026'] - pred_bat['woba']).round(3)
        st.dataframe(
            pred_bat[['Name', 'woba', 'woba_pred_2026', 'diferencia', 'tendencia']].rename(columns={
                'woba': 'wOBA 2025',
                'woba_pred_2026': 'wOBA pred 2026',
                'diferencia': 'Diff',
                'tendencia': 'Tendencia'
            }).sort_values('wOBA pred 2026', ascending=False),
            hide_index=True,
            height=450
        )

    with col2:
        st.markdown("#### Pitchers")
        pred_pit['tendencia'] = pred_pit.apply(
            lambda r: '📈 Mejora' if r['xera_pred_2026'] < r['xera'] else '📉 Empeora', axis=1
        )
        pred_pit['diferencia'] = (pred_pit['xera_pred_2026'] - pred_pit['xera']).round(2)
        st.dataframe(
            pred_pit[['Name', 'xera', 'xera_pred_2026', 'diferencia', 'tendencia']].rename(columns={
                'xera': 'xERA 2025',
                'xera_pred_2026': 'xERA pred 2026',
                'diferencia': 'Diff',
                'tendencia': 'Tendencia'
            }).sort_values('xERA pred 2026', ascending=True),
            hide_index=True,
            height=450
        )

# TAB 4 - ALERTAS
with tab4:
    st.subheader("⚠️ Alertas de la semana")

    col1, col2 = st.columns(2)

    with col1:
        st.success("📈 COMPRAR — Bateadores con upside")
        comprando = pred_bat[pred_bat['diferencia'] > 0.015].sort_values('diferencia', ascending=False)
        for _, r in comprando.iterrows():
            st.markdown(f"**{r['Name']}** — xwOBA sugiere +{r['diferencia']:.3f} mejora")

        st.divider()
        st.error("📉 VENDER — Bateadores en declive")
        vendiendo = pred_bat[pred_bat['diferencia'] < -0.015].sort_values('diferencia')
        for _, r in vendiendo.iterrows():
            st.markdown(f"**{r['Name']}** — proyección baja {r['diferencia']:.3f}")

    with col2:
        st.warning("⚠️ RIESGO — Pitchers con suerte (xERA >> ERA)")
        riesgo_pit = pitcheo[pitcheo['xera'] - pitcheo['p_era'] > 0.50].sort_values('p_era')
        for _, r in riesgo_pit.iterrows():
            diff = r['xera'] - r['p_era']
            st.markdown(f"**{r['Name']}** — ERA {r['p_era']:.2f} pero xERA {r['xera']:.2f} (+{diff:.2f})")

        st.divider()
        st.success("✅ CONFIABLES — Pitchers sólidos")
        confiables = pitcheo[pitcheo['score'] >= 70]
        for _, r in confiables.iterrows():
            st.markdown(f"**{r['Name']}** — Score {r['score']:.0f}, ERA {r['p_era']:.2f}")