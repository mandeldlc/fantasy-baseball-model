import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Liga Fantasy Baseball 2026",
    page_icon="🏆",
    layout="wide"
)

@st.cache_data(ttl=3600)
def load_odds():
    try:
        return pd.read_csv('data/liga_odds.csv')
    except:
        return None

df = load_odds()

st.title("🏆 Liga Fantasy Baseball 2026")
st.caption(f"Probabilidades actualizadas — {datetime.now().strftime('%B %d, %Y')}")
st.divider()

if df is None:
    st.error("No hay datos disponibles aún.")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        t = df.iloc[0]
        st.metric("🥇 Favorito", t['team_name'], f"{t['prob_camp']:.1f}% — {t['odds']}")
    with col2:
        t = df.iloc[1]
        st.metric("🥈 Segundo", t['team_name'], f"{t['prob_camp']:.1f}% — {t['odds']}")
    with col3:
        t = df.iloc[2]
        st.metric("🥉 Tercero", t['team_name'], f"{t['prob_camp']:.1f}% — {t['odds']}")

    st.divider()

    st.subheader("📊 Tabla de Probabilidades")
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            df.sort_values('prob_camp'),
            x='prob_camp',
            y='team_name',
            orientation='h',
            color='prob_camp',
            color_continuous_scale=['red', 'yellow', 'green'],
            title='Probabilidad de Campeonato por Equipo',
            labels={'prob_camp': 'Probabilidad %', 'team_name': ''}
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(
            df[['rank', 'team_name', 'prob_camp', 'odds']].rename(columns={
                'rank': '#',
                'team_name': 'Equipo',
                'prob_camp': 'Prob %',
                'odds': 'Odds'
            }),
            hide_index=True,
            height=500
        )

    st.divider()

    st.subheader("🎰 Odds Completos")

    col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 2, 2, 2, 2, 2, 2])
    with col1:
        st.markdown("**Equipo**")
    with col2:
        st.markdown("**Odds**")
    with col3:
        st.markdown("**Prob. hoy**")
    with col4:
        st.markdown("**Proj. inicial**")
    with col5:
        st.markdown("**Cambio**")
    with col6:
        st.markdown("**W-L-T**")
    with col7:
        st.markdown("**Tendencia**")

    st.divider()

    for _, r in df.iterrows():
        col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 2, 2, 2, 2, 2, 2])
        rank_emoji = "🏆" if r['rank'] == 1 else "🔥" if r['rank'] <= 3 else "⚾"
        prob_inicial = r.get('prob_inicial', r['prob_camp'])
        diff = r.get('diff', 0)
        tendencia = r.get('tendencia', '➡️')
        wins = int(r.get('wins', 0))
        losses = int(r.get('losses', 0))

        with col1:
            st.markdown(f"{rank_emoji} **{r['team_name']}**")
        with col2:
            st.markdown(f"**{r['odds']}**")
        with col3:
            st.markdown(f"**{r['prob_camp']:.1f}%**")
        with col4:
            st.markdown(f"{prob_inicial:.1f}%")
        with col5:
            color = "green" if diff > 0 else "red" if diff < 0 else "gray"
            signo = "+" if diff > 0 else ""
            st.markdown(f":{color}[{signo}{diff:.1f}%]")
        with col6:
            st.markdown(f"{wins}-{losses}-{int(r.get('ties', 0))}")
        with col7:
            st.markdown(f"**{tendencia}**")

    st.divider()
    st.caption("⚠️ Probabilidades calculadas con modelo ML — roster (50%) + record W-L (30%) + historial felo (20%). No representan apuestas reales.")