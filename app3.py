import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from nba_api.stats.endpoints import PlayerGameLog
from nba_api.stats.static import players, teams

# Retrieve player ID
def get_player_id(player_name):
    player_list = players.get_players()
    for player in player_list:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    return None

# Retrieve team ID
def get_team_id(team_name):
    team_list = teams.get_teams()
    for team in team_list:
        if team['full_name'].lower() == team_name.lower():
            return team['id']
    return None

# Retrieve team abbreviation
def get_team_abbreviation(team_id):
    team_list = teams.get_teams()
    for team in team_list:
        if team['id'] == team_id:
            return team['abbreviation']
    return None

# Fetch player game logs
def get_game_logs(player_name, team_name=None, seasons=None, last_n_games=15):
    player_id = get_player_id(player_name)
    if not player_id:
        st.warning(f"⚠️ Player '{player_name}' not found! Check the name.")
        return None

    if team_name and seasons:
        team_id = get_team_id(team_name)
        if not team_id:
            st.warning(f"⚠️ Team '{team_name}' not found! Check the name.")
            return None

        team_abbreviation = get_team_abbreviation(team_id)
        if not team_abbreviation:
            st.warning(f"⚠️ Could not find abbreviation for team '{team_name}'.")
            return None

        all_logs = []
        for season in seasons:
            gamelog = PlayerGameLog(player_id=player_id, season=season)
            df = gamelog.get_data_frames()[0]
            df = df[df['MATCHUP'].str.contains(team_abbreviation)]
            all_logs.append(df)

        return pd.concat(all_logs, ignore_index=True) if all_logs else None

    # Fetch last N games
    gamelog = PlayerGameLog(player_id=player_id)
    df = gamelog.get_data_frames()[0]
    return df.head(last_n_games)

# Visualization
def plot_combined_graphs(last_15_df, matchup_df, player_name, team_name):
    fig = make_subplots(
        rows=2, cols=2, 
        subplot_titles=[
            f"🏀 {player_name} - Points (PTS)",
            f"📊 {player_name} - Rebounds (REB)",
            f"🎯 {player_name} - Assists (AST)",
            f"🔥 {player_name} vs. {team_name or 'All Teams'} (PRA)"
        ],
        horizontal_spacing=0.12, vertical_spacing=0.15
    )

    if last_15_df is not None and not last_15_df.empty:
        last_15_df["GAME_DATE"] = pd.to_datetime(last_15_df["GAME_DATE"])
        last_15_df = last_15_df.sort_values("GAME_DATE")
        last_15_df[['PTS', 'REB', 'AST']] = last_15_df[['PTS', 'REB', 'AST']].apply(pd.to_numeric)
        last_15_df["Game Date"] = last_15_df["GAME_DATE"].dt.strftime('%b %d')

        # Colors for bars
        avg_pts, avg_reb, avg_ast = last_15_df["PTS"].mean(), last_15_df["REB"].mean(), last_15_df["AST"].mean()
        colors_pts = ["#4CAF50" if pts > avg_pts else "#2196F3" for pts in last_15_df["PTS"]]
        colors_reb = ["#FFA726" if reb > avg_reb else "#FFEB3B" for reb in last_15_df["REB"]]
        colors_ast = ["#AB47BC" if ast > avg_ast else "#9575CD" for ast in last_15_df["AST"]]

        # Points with hover info
        fig.add_trace(go.Bar(
            x=last_15_df["Game Date"],
            y=last_15_df["PTS"],
            text=[f"<b>{pts} PTS</b><br>{reb} REB | {ast} AST" for pts, reb, ast in zip(last_15_df["PTS"], last_15_df["REB"], last_15_df["AST"])],
            hoverinfo="text",
            marker=dict(color=colors_pts)
        ), row=1, col=1)

        # Rebounds with hover info
        fig.add_trace(go.Bar(
            x=last_15_df["Game Date"],
            y=last_15_df["REB"],
            text=[f"<b>{reb} REB</b><br>{pts} PTS | {ast} AST" for pts, reb, ast in zip(last_15_df["PTS"], last_15_df["REB"], last_15_df["AST"])],
            hoverinfo="text",
            marker=dict(color=colors_reb)
        ), row=1, col=2)

        # Assists with hover info
        fig.add_trace(go.Bar(
            x=last_15_df["Game Date"],
            y=last_15_df["AST"],
            text=[f"<b>{ast} AST</b><br>{pts} PTS | {reb} REB" for pts, reb, ast in zip(last_15_df["PTS"], last_15_df["REB"], last_15_df["AST"])],
            hoverinfo="text",
            marker=dict(color=colors_ast)
        ), row=2, col=1)

    if matchup_df is not None and not matchup_df.empty:
        matchup_df["GAME_DATE"] = pd.to_datetime(matchup_df["GAME_DATE"])
        matchup_df = matchup_df.sort_values("GAME_DATE")
        matchup_df["PRA"] = matchup_df["PTS"] + matchup_df["REB"] + matchup_df["AST"]
        matchup_df["Game Date"] = matchup_df["GAME_DATE"].dt.strftime('%Y-%m-%d')

        avg_pra = matchup_df["PRA"].mean()
        colors_pra = ["#FF3D00" if pra > avg_pra else "#FF8A65" for pra in matchup_df["PRA"]]

        # PRA with hover info
        fig.add_trace(go.Bar(
            x=matchup_df["Game Date"],
            y=matchup_df["PRA"],
            text=[f"<b>{pra} PRA</b><br>{pts} PTS | {reb} REB | {ast} AST" for pts, reb, ast, pra in zip(matchup_df["PTS"], matchup_df["REB"], matchup_df["AST"], matchup_df["PRA"])],
            hoverinfo="text",
            marker=dict(color=colors_pra)
        ), row=2, col=2)

    fig.update_layout(title_text=f"{player_name} Performance Analysis", template="plotly_dark", height=800, width=1200)
    st.plotly_chart(fig)

# Streamlit UI
st.title("🏀 NBA Player Performance Dashboard")

player_name = st.text_input("Enter player name:", "LeBron James")
team_name = st.text_input("Enter opponent team (optional):", "")

last_15_df = get_game_logs(player_name, last_n_games=15)
matchup_df = None
if team_name:
    last_three_seasons = ["2024-25", "2023-24", "2022-23"]
    matchup_df = get_game_logs(player_name, team_name, last_three_seasons)

if last_15_df is not None or matchup_df is not None:
    plot_combined_graphs(last_15_df, matchup_df, player_name, team_name)
