import re
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Copa do Mundo FIFA",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.82rem; color: #aaa; }
    [data-testid="stMetricDelta"] { font-size: 0.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────── CARGA E LIMPEZA ─────────────────────────────
@st.cache_data
def load_data():
    cups = pd.read_csv("data/WorldCups.csv")
    matches = pd.read_csv("data/WorldCupMatches.csv")
    players = pd.read_csv("data/WorldCupPlayers.csv")

    # WorldCups: attendance usa ponto como separador de milhar (padrão europeu)
    cups["Attendance"] = (
        cups["Attendance"].astype(str).str.replace(".", "", regex=False).str.strip()
    )
    cups["Attendance"] = pd.to_numeric(cups["Attendance"], errors="coerce")
    cups["Year"] = cups["Year"].astype(int)

    # Matches
    matches = matches.dropna(subset=["Year", "Home Team Name", "Away Team Name"])
    matches["Year"] = matches["Year"].astype(int)
    matches["Home Team Goals"] = pd.to_numeric(
        matches["Home Team Goals"], errors="coerce"
    ).fillna(0).astype(int)
    matches["Away Team Goals"] = pd.to_numeric(
        matches["Away Team Goals"], errors="coerce"
    ).fillna(0).astype(int)
    matches["Total Goals"] = matches["Home Team Goals"] + matches["Away Team Goals"]
    matches["Attendance"] = pd.to_numeric(matches["Attendance"], errors="coerce")
    matches["Home Team Name"] = matches["Home Team Name"].str.strip()
    matches["Away Team Name"] = matches["Away Team Name"].str.strip()
    matches["City"] = matches["City"].str.strip()

    # Players: parse eventos (G = gol, OG = gol-contra, Y = amarelo, R = vermelho)
    def _count(event, prefix):
        if pd.isna(event) or str(event).strip() == "":
            return 0
        return sum(
            1 for tok in str(event).split() if re.match(rf"^{prefix}\d+", tok)
        )

    players["Goals"] = players["Event"].apply(lambda e: _count(e, "G") - _count(e, "OG"))
    players["Goals"] = players["Goals"].clip(lower=0)
    players["OwnGoals"] = players["Event"].apply(lambda e: _count(e, "OG"))
    players["YellowCards"] = players["Event"].apply(lambda e: _count(e, "Y"))
    players["RedCards"] = players["Event"].apply(lambda e: _count(e, "R"))

    return cups, matches, players


cups, matches, players = load_data()


# ─────────────────────────────── SIDEBAR ─────────────────────────────────────
st.sidebar.title("⚽ Copa do Mundo FIFA")
st.sidebar.caption("Dashboard histórico 1930 – 2014")
st.sidebar.divider()

years = sorted(cups["Year"].unique())
year_range = st.sidebar.select_slider(
    "Período da análise",
    options=years,
    value=(years[0], years[-1]),
    format_func=str,
)

all_teams = sorted(
    set(matches["Home Team Name"].unique()) | set(matches["Away Team Name"].unique())
)
selected_teams = st.sidebar.multiselect(
    "Filtrar seleções (opcional)", options=all_teams, default=[]
)

st.sidebar.divider()
st.sidebar.info("Fonte: FIFA World Cup Historical Dataset")


# ─────────────────────────────── FILTROS ─────────────────────────────────────
cups_f = cups[
    cups["Year"].between(year_range[0], year_range[1])
].copy()

matches_f = matches[
    matches["Year"].between(year_range[0], year_range[1])
].copy()

if selected_teams:
    matches_f = matches_f[
        matches_f["Home Team Name"].isin(selected_teams)
        | matches_f["Away Team Name"].isin(selected_teams)
    ]


# ─────────────────────────────── CABEÇALHO ───────────────────────────────────
st.title("🏆 Copa do Mundo FIFA — Dashboard Interativo")
st.markdown(
    f"Análise histórica de **{year_range[0]}** a **{year_range[1]}** "
    f"· **{len(cups_f)} edições**"
    + (f"  ·  Filtro: {', '.join(selected_teams)}" if selected_teams else "")
)
st.divider()


# ─────────────────────────────── KPIs ─────────────────────────────────────────
total_goals = int(cups_f["GoalsScored"].sum())
total_matches = int(cups_f["MatchesPlayed"].sum())
total_attendance = cups_f["Attendance"].sum()
avg_gpm = round(total_goals / total_matches, 2) if total_matches else 0
winner_vc = cups_f["Winner"].value_counts()
top_winner = winner_vc.idxmax()
top_winner_n = int(winner_vc.max())
max_attendance_row = cups_f.loc[cups_f["Attendance"].idxmax()]

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Edições", len(cups_f))
col2.metric("Gols Marcados", f"{total_goals:,}")
col3.metric("Jogos Realizados", f"{total_matches:,}")
col4.metric("Público Acumulado", f"{int(total_attendance):,}")
col5.metric("Média Gols/Jogo", avg_gpm)
col6.metric("Maior Campeão", f"{top_winner}", f"{top_winner_n} títulos")

st.divider()


# ─────────────────────────────── ABAS ─────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Visão Geral", "🌍 Seleções", "⚽ Partidas", "👤 Jogadores"]
)


# ════════════════════════════ ABA 1 — VISÃO GERAL ════════════════════════════
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            cups_f,
            x="Year",
            y="GoalsScored",
            title="Gols Marcados por Edição",
            color="GoalsScored",
            color_continuous_scale="RdYlGn",
            labels={"GoalsScored": "Gols", "Year": "Ano"},
            text="GoalsScored",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.area(
            cups_f,
            x="Year",
            y="Attendance",
            title="Público Total por Edição",
            markers=True,
            labels={"Attendance": "Público", "Year": "Ano"},
            color_discrete_sequence=["#3498db"],
        )
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        cups_f["GolsPorJogo"] = (
            cups_f["GoalsScored"] / cups_f["MatchesPlayed"]
        ).round(2)
        fig = px.line(
            cups_f,
            x="Year",
            y="GolsPorJogo",
            title="Média de Gols por Jogo",
            markers=True,
            labels={"Year": "Ano", "GolsPorJogo": "Gols/Jogo"},
            color_discrete_sequence=["#e74c3c"],
        )
        fig.update_traces(fill="tozeroy", fillcolor="rgba(231,76,60,0.12)")
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = px.bar(
            cups_f,
            x="Year",
            y="QualifiedTeams",
            title="Seleções Participantes por Edição",
            color="QualifiedTeams",
            color_continuous_scale="Purples",
            labels={"QualifiedTeams": "Seleções", "Year": "Ano"},
            text="QualifiedTeams",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Histórico Completo das Edições")
    disp = cups_f[
        ["Year", "Country", "Winner", "Runners-Up", "Third", "Fourth",
         "GoalsScored", "MatchesPlayed", "Attendance", "QualifiedTeams"]
    ].rename(columns={
        "Year": "Ano", "Country": "Sede", "Winner": "Campeão",
        "Runners-Up": "2º Lugar", "Third": "3º Lugar", "Fourth": "4º Lugar",
        "GoalsScored": "Gols", "MatchesPlayed": "Jogos",
        "Attendance": "Público", "QualifiedTeams": "Seleções",
    })
    st.dataframe(disp.reset_index(drop=True), use_container_width=True, hide_index=True)


# ════════════════════════════ ABA 2 — SELEÇÕES ═══════════════════════════════
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        winners = cups_f["Winner"].value_counts().reset_index()
        winners.columns = ["País", "Títulos"]
        fig = px.bar(
            winners,
            x="Títulos",
            y="País",
            orientation="h",
            title="Países Campeões do Mundo",
            color="Títulos",
            color_continuous_scale="YlOrRd",
            text="Títulos",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.pie(
            winners,
            names="País",
            values="Títulos",
            title="Distribuição dos Títulos Mundiais",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        finalists = pd.concat([
            cups_f[["Winner"]].rename(columns={"Winner": "Team"}),
            cups_f[["Runners-Up"]].rename(columns={"Runners-Up": "Team"}),
        ])
        fin_counts = finalists["Team"].value_counts().head(12).reset_index()
        fin_counts.columns = ["País", "Finais"]
        fig = px.bar(
            fin_counts,
            x="Finais",
            y="País",
            orientation="h",
            title="Países com Mais Finais Disputadas",
            color="Finais",
            color_continuous_scale="Blues",
            text="Finais",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        podium = pd.concat([
            cups_f[["Winner"]].rename(columns={"Winner": "Team"}),
            cups_f[["Runners-Up"]].rename(columns={"Runners-Up": "Team"}),
            cups_f[["Third"]].rename(columns={"Third": "Team"}),
        ])
        pod_counts = podium["Team"].value_counts().head(12).reset_index()
        pod_counts.columns = ["País", "Pódios"]
        fig = px.bar(
            pod_counts,
            x="Pódios",
            y="País",
            orientation="h",
            title="Países com Mais Pódios (Top 3)",
            color="Pódios",
            color_continuous_scale="Greens",
            text="Pódios",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Desempenho das Seleções nas Partidas")

    home_s = (
        matches_f.groupby("Home Team Name")
        .agg(Jogos=("MatchID", "count"),
             GolsMarcados=("Home Team Goals", "sum"),
             GolsSofridos=("Away Team Goals", "sum"))
        .reset_index()
        .rename(columns={"Home Team Name": "Seleção"})
    )
    away_s = (
        matches_f.groupby("Away Team Name")
        .agg(Jogos=("MatchID", "count"),
             GolsMarcados=("Away Team Goals", "sum"),
             GolsSofridos=("Home Team Goals", "sum"))
        .reset_index()
        .rename(columns={"Away Team Name": "Seleção"})
    )
    team_stats = pd.concat([home_s, away_s]).groupby("Seleção").sum().reset_index()
    team_stats["Saldo"] = team_stats["GolsMarcados"] - team_stats["GolsSofridos"]
    team_stats = team_stats.sort_values("GolsMarcados", ascending=False).head(20)

    fig = px.bar(
        team_stats,
        x="Seleção",
        y=["GolsMarcados", "GolsSofridos"],
        title="Top 20 Seleções — Gols Marcados vs Sofridos",
        barmode="group",
        labels={"value": "Gols", "variable": "", "Seleção": ""},
        color_discrete_map={"GolsMarcados": "#2ecc71", "GolsSofridos": "#e74c3c"},
    )
    fig.update_layout(xaxis_tickangle=45, legend_title_text="")
    fig.for_each_trace(
        lambda t: t.update(
            name="Marcados" if t.name == "GolsMarcados" else "Sofridos"
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # Saldo de gols (scatter)
    fig2 = px.scatter(
        team_stats,
        x="GolsMarcados",
        y="GolsSofridos",
        size="Jogos",
        color="Saldo",
        text="Seleção",
        title="Gols Marcados × Sofridos (tamanho = nº de jogos, cor = saldo)",
        color_continuous_scale="RdYlGn",
        labels={"GolsMarcados": "Marcados", "GolsSofridos": "Sofridos"},
    )
    fig2.update_traces(textposition="top center")
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════ ABA 3 — PARTIDAS ═══════════════════════════════
with tab3:

    def classify_stage(s):
        if pd.isna(s):
            return "Outros"
        sl = str(s).lower()
        if "semi" in sl:
            return "Semifinal"
        if "quarter" in sl:
            return "Quartas de Final"
        if "round of 16" in sl or "second round" in sl:
            return "Oitavas de Final"
        if ("final" in sl
                and "quarter" not in sl
                and "semi" not in sl
                and "third" not in sl
                and "play" not in sl):
            return "Final"
        if "third" in sl or "play" in sl:
            return "3º Lugar"
        if "preliminary" in sl:
            return "Preliminar"
        if "group" in sl:
            return "Fase de Grupos"
        return "Outros"

    matches_f["Fase"] = matches_f["Stage"].apply(classify_stage)

    c1, c2 = st.columns(2)

    with c1:
        stage_agg = (
            matches_f.groupby("Fase")
            .agg(MediaGols=("Total Goals", "mean"), Jogos=("MatchID", "count"))
            .reset_index()
        )
        stage_agg["MediaGols"] = stage_agg["MediaGols"].round(2)
        stage_agg = stage_agg.sort_values("MediaGols")
        fig = px.bar(
            stage_agg,
            x="MediaGols",
            y="Fase",
            orientation="h",
            title="Média de Gols por Fase",
            color="MediaGols",
            color_continuous_scale="RdYlGn",
            text="MediaGols",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        home_total = int(matches_f["Home Team Goals"].sum())
        away_total = int(matches_f["Away Team Goals"].sum())
        fig = go.Figure(go.Pie(
            labels=["Mandante", "Visitante"],
            values=[home_total, away_total],
            hole=0.5,
            marker_colors=["#3498db", "#e74c3c"],
            textinfo="label+percent+value",
        ))
        fig.update_layout(title="Gols: Mandante vs Visitante")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        gpy = (
            matches_f.groupby("Year")
            .agg(TotalGols=("Total Goals", "sum"), Jogos=("MatchID", "count"))
            .reset_index()
        )
        gpy["Media"] = (gpy["TotalGols"] / gpy["Jogos"]).round(2)
        fig = px.line(
            gpy,
            x="Year",
            y="Media",
            title="Evolução da Média de Gols por Jogo",
            markers=True,
            labels={"Year": "Ano", "Media": "Gols/Jogo"},
            color_discrete_sequence=["#f39c12"],
        )
        fig.update_traces(fill="tozeroy", fillcolor="rgba(243,156,18,0.12)")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = px.histogram(
            matches_f.dropna(subset=["Attendance"]),
            x="Attendance",
            nbins=40,
            title="Distribuição do Público por Partida",
            labels={"Attendance": "Público", "count": "Nº de Partidas"},
            color_discrete_sequence=["#9b59b6"],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Gols por ano — caixa
    fig_box = px.box(
        matches_f,
        x="Year",
        y="Total Goals",
        title="Distribuição de Gols por Partida — Cada Edição",
        labels={"Year": "Ano", "Total Goals": "Gols na Partida"},
        color_discrete_sequence=["#1abc9c"],
    )
    fig_box.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig_box, use_container_width=True)

    c5, c6 = st.columns(2)

    with c5:
        st.subheader("Partidas com Maior Público")
        top_att = matches_f.nlargest(10, "Attendance")[[
            "Year", "Stage", "Home Team Name", "Home Team Goals",
            "Away Team Goals", "Away Team Name", "City", "Attendance",
        ]].rename(columns={
            "Year": "Ano", "Stage": "Fase", "Home Team Name": "Mandante",
            "Home Team Goals": "GM", "Away Team Goals": "GV",
            "Away Team Name": "Visitante", "City": "Cidade", "Attendance": "Público",
        })
        st.dataframe(top_att, use_container_width=True, hide_index=True)

    with c6:
        st.subheader("Partidas com Mais Gols")
        top_gls = matches_f.nlargest(10, "Total Goals")[[
            "Year", "Stage", "Home Team Name", "Home Team Goals",
            "Away Team Goals", "Away Team Name", "Total Goals",
        ]].rename(columns={
            "Year": "Ano", "Stage": "Fase", "Home Team Name": "Mandante",
            "Home Team Goals": "GM", "Away Team Goals": "GV",
            "Away Team Name": "Visitante", "Total Goals": "Total",
        })
        st.dataframe(top_gls, use_container_width=True, hide_index=True)


# ════════════════════════════ ABA 4 — JOGADORES ══════════════════════════════
with tab4:
    players_ext = players.merge(
        matches[["MatchID", "Year"]].drop_duplicates(), on="MatchID", how="left"
    )
    players_f = players_ext[
        players_ext["Year"].between(year_range[0], year_range[1])
    ].copy()

    c1, c2 = st.columns(2)

    with c1:
        scorers = (
            players_f.groupby("Player Name")["Goals"]
            .sum()
            .reset_index()
            .query("Goals > 0")
            .sort_values("Goals", ascending=False)
            .head(15)
        )
        scorers.columns = ["Jogador", "Gols"]
        fig = px.bar(
            scorers,
            x="Gols",
            y="Jogador",
            orientation="h",
            title="Top 15 Artilheiros Históricos",
            color="Gols",
            color_continuous_scale="Reds",
            text="Gols",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        team_goals = (
            players_f.groupby("Team Initials")["Goals"]
            .sum()
            .reset_index()
            .query("Goals > 0")
            .sort_values("Goals", ascending=False)
            .head(15)
        )
        team_goals.columns = ["Seleção", "Gols"]
        fig = px.bar(
            team_goals,
            x="Gols",
            y="Seleção",
            orientation="h",
            title="Top 15 Seleções — Gols por Jogadores",
            color="Gols",
            color_continuous_scale="Blues",
            text="Gols",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        cards = (
            players_f.groupby("Team Initials")
            .agg(Amarelos=("YellowCards", "sum"), Vermelhos=("RedCards", "sum"))
            .reset_index()
        )
        cards["Total"] = cards["Amarelos"] + cards["Vermelhos"]
        cards = cards[cards["Total"] > 0].sort_values("Total", ascending=False).head(15)
        fig = px.bar(
            cards,
            x="Team Initials",
            y=["Amarelos", "Vermelhos"],
            title="Top 15 Seleções — Cartões",
            barmode="stack",
            color_discrete_map={"Amarelos": "#f1c40f", "Vermelhos": "#c0392b"},
            labels={"Team Initials": "Seleção", "value": "Cartões", "variable": ""},
        )
        fig.update_layout(xaxis_tickangle=45, legend_title_text="")
        fig.for_each_trace(
            lambda t: t.update(
                name="Amarelo" if t.name == "Amarelos" else "Vermelho"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        def extract_minutes(event):
            if pd.isna(event) or str(event).strip() == "":
                return []
            return [
                int(m)
                for tok in str(event).split()
                for m in re.findall(r"^G(\d+)", tok)
            ]

        all_minutes = []
        for ev in players_f["Event"]:
            all_minutes.extend(extract_minutes(ev))

        if all_minutes:
            mins_df = pd.DataFrame({"Minuto": all_minutes})
            mins_df = mins_df[mins_df["Minuto"].between(1, 120)]
            fig = px.histogram(
                mins_df,
                x="Minuto",
                nbins=24,
                title="Distribuição dos Gols por Minuto de Jogo",
                labels={"Minuto": "Minuto", "count": "Gols"},
                color_discrete_sequence=["#27ae60"],
            )
            fig.add_vline(
                x=45, line_dash="dash", line_color="red",
                annotation_text="Intervalo", annotation_position="top right",
            )
            fig.add_vline(
                x=90, line_dash="dash", line_color="orange",
                annotation_text="Tempo Normal", annotation_position="top right",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Gols próprios por seleção
    og_by_team = (
        players_f.groupby("Team Initials")["OwnGoals"]
        .sum()
        .reset_index()
        .query("OwnGoals > 0")
        .sort_values("OwnGoals", ascending=False)
        .head(10)
    )
    og_by_team.columns = ["Seleção", "Gols Contra"]

    c5, c6 = st.columns(2)

    with c5:
        fig = px.bar(
            og_by_team,
            x="Gols Contra",
            y="Seleção",
            orientation="h",
            title="Top 10 Seleções com Mais Gols Contra",
            color="Gols Contra",
            color_continuous_scale="OrRd",
            text="Gols Contra",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        # Artilheiros por edição
        top_by_year = (
            players_f.groupby(["Year", "Player Name", "Team Initials"])["Goals"]
            .sum()
            .reset_index()
            .query("Goals > 0")
        )
        top_by_year = (
            top_by_year.sort_values(["Year", "Goals"], ascending=[True, False])
            .groupby("Year")
            .head(1)
            .reset_index(drop=True)
        )
        top_by_year.columns = ["Ano", "Artilheiro", "Seleção", "Gols"]
        st.subheader("Artilheiro de Cada Edição")
        st.dataframe(top_by_year, use_container_width=True, hide_index=True)


# ─────────────────────────────── RODAPÉ ──────────────────────────────────────
st.divider()
st.caption(
    "📊 Fonte: FIFA World Cup Historical Dataset (Kaggle)  |  "
    "Dashboard: Streamlit · Plotly · Pandas"
)
