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
def get_game_logs(player_name, last_n_games=15, location_filter="All"):
    player_id = get_player_id(player_name)
    if not player_id:
        st.warning(f"⚠️ Player '{player_name}' not found! Check the name.")
        return None

    gamelog = PlayerGameLog(player_id=player_id)
    df = gamelog.get_data_frames()[0]
    
    # Extract opponent and home/away info
    df["LOCATION"] = df["MATCHUP"].apply(lambda x: "Home" if " vs. " in x else "Away")
    df["OPPONENT"] = df["MATCHUP"].apply(lambda x: x.split(" vs. ")[-1] if " vs. " in x else x.split(" @ ")[-1])

    # Apply location filter
    if location_filter == "Home":
        df = df[df["LOCATION"] == "Home"]
    elif location_filter == "Away":
        df = df[df["LOCATION"] == "Away"]

    return df.head(last_n_games)

# Visualization
def plot_combined_graphs(df, player_name):
    if df is None or df.empty:
        st.warning("⚠️ No data available for selected filters.")
        return

    fig = make_subplots(
        rows=2, cols=2, 
        subplot_titles=[
            f"🏀 {player_name} - Points (PTS)",
            f"📊 {player_name} - Rebounds (REB)",
            f"🎯 {player_name} - Assists (AST)",
            f"🔥 {player_name} - PRA (Points + Rebounds + Assists)"
        ],
        horizontal_spacing=0.12, vertical_spacing=0.15
    )

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df[::-1]
    df[['PTS', 'REB', 'AST']] = df[['PTS', 'REB', 'AST']].apply(pd.to_numeric)
    df["Game Label"] = df["GAME_DATE"].dt.strftime('%b %d') + " vs " + df["OPPONENT"] + " (" + df["LOCATION"] + ")"

    avg_pts, avg_reb, avg_ast = df["PTS"].mean(), df["REB"].mean(), df["AST"].mean()
    colors_pts = ["#4CAF50" if pts > avg_pts else "#2196F3" for pts in df["PTS"]]
    colors_reb = ["#FFA726" if reb > avg_reb else "#FFEB3B" for reb in df["REB"]]
    colors_ast = ["#AB47BC" if ast > avg_ast else "#9575CD" for ast in df["AST"]]

    # Points
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["PTS"], marker=dict(color=colors_pts)), row=1, col=1)
    fig.add_hline(y=avg_pts, line_dash="dash", line_color="gray", row=1, col=1, annotation_text=f"Avg PTS: {avg_pts:.1f}")

    # Rebounds
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["REB"], marker=dict(color=colors_reb)), row=1, col=2)
    fig.add_hline(y=avg_reb, line_dash="dash", line_color="gray", row=1, col=2, annotation_text=f"Avg REB: {avg_reb:.1f}")

    # Assists
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["AST"], marker=dict(color=colors_ast)), row=2, col=1)
    fig.add_hline(y=avg_ast, line_dash="dash", line_color="gray", row=2, col=1, annotation_text=f"Avg AST: {avg_ast:.1f}")

    # PRA
    df["PRA"] = df["PTS"] + df["REB"] + df["AST"]
    avg_pra = df["PRA"].mean()
    colors_pra = ["#FF3D00" if pra > avg_pra else "#FF8A65" for pra in df["PRA"]]

    fig.add_trace(go.Bar(x=df["Game Label"], y=df["PRA"], marker=dict(color=colors_pra)), row=2, col=2)
    fig.add_hline(y=avg_pra, line_dash="dash", line_color="gray", row=2, col=2, annotation_text=f"Avg PRA: {avg_pra:.1f}")

    fig.update_layout(title_text=f"{player_name} Performance Analysis", template="plotly_dark", height=800, width=1200)
    st.plotly_chart(fig)

# Streamlit UI
st.title("🏀 NBA Player Performance Dashboard")

# Get player input
player_name = st.text_input("Enter player name:", "LeBron James")

# Location filter
location_filter = st.radio("Filter Games:", ["All", "Home", "Away"], index=0)

# Fetch Data
df = get_game_logs(player_name, last_n_games=15, location_filter=location_filter)

# Show DataFrame
if df is not None:
    st.subheader(f"📊 Last 15 {location_filter} Games - {player_name}")
    st.dataframe(df[['GAME_DATE', 'MATCHUP', 'LOCATION', 'OPPONENT', 'PTS', 'REB', 'AST']])

# Plot Graphs
plot_combined_graphs(df, player_name)

