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

# Fetch logs against a specific opponent
def get_game_logs_vs_team(player_name, opponent_name, seasons):
    player_id = get_player_id(player_name)
    opponent_id = get_team_id(opponent_name)
    
    if not player_id or not opponent_id:
        st.warning("⚠️ Player or Team not found! Check the name.")
        return None

    opponent_abbreviation = get_team_abbreviation(opponent_id)
    
    all_logs = []
    for season in seasons:
        gamelog = PlayerGameLog(player_id=player_id, season=season)
        df = gamelog.get_data_frames()[0]
        
        # Filter only games against the specific opponent
        df = df[df["MATCHUP"].str.contains(opponent_abbreviation)]
        
        # Extract opponent and home/away info
        df["LOCATION"] = df["MATCHUP"].apply(lambda x: "Home" if " vs. " in x else "Away")
        df["OPPONENT"] = opponent_name

        all_logs.append(df)

    return pd.concat(all_logs, ignore_index=True) if all_logs else None

# Visualization
def plot_combined_graphs(df, matchup_df, player_name, opponent_name):
    if df is None or df.empty:
        st.warning("⚠️ No data available for selected filters.")
        return

    fig = make_subplots(
        rows=3, cols=2, 
        subplot_titles=[
            f"🏀 {player_name} - Points (PTS)",
            f"📊 {player_name} - Rebounds (REB)",
            f"🎯 {player_name} - Assists (AST)",
            f"🔥 {player_name} - PRA (PTS+REB+AST)",
            f"⚔️ {player_name} vs. {opponent_name} - PRA (Last 3 Seasons)"
        ],
        horizontal_spacing=0.12, vertical_spacing=0.15,
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar", "colspan": 2}, None]]
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

    # Rebounds
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["REB"], marker=dict(color=colors_reb)), row=1, col=2)

    # Assists
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["AST"], marker=dict(color=colors_ast)), row=2, col=1)

    # PRA
    df["PRA"] = df["PTS"] + df["REB"] + df["AST"]
    colors_pra = ["#FF3D00" if pra > df["PRA"].mean() else "#FF8A65" for pra in df["PRA"]]
    fig.add_trace(go.Bar(x=df["Game Label"], y=df["PRA"], marker=dict(color=colors_pra)), row=2, col=2)

    # PRA vs Opponent
    if matchup_df is not None and not matchup_df.empty:
        matchup_df["GAME_DATE"] = pd.to_datetime(matchup_df["GAME_DATE"])
        matchup_df["PRA"] = matchup_df["PTS"] + matchup_df["REB"] + matchup_df["AST"]
        fig.add_trace(go.Bar(x=matchup_df["GAME_DATE"].dt.strftime('%Y-%m-%d'), y=matchup_df["PRA"], marker=dict(color="#FF6F00")), row=3, col=1)

    fig.update_layout(title_text=f"{player_name} Performance Analysis", template="plotly_dark", height=1000, width=1400)
    st.plotly_chart(fig)

# Streamlit UI
st.title("🏀 NBA Player Performance Dashboard")

# Get player input
player_name = st.text_input("Enter player name:", "LeBron James")

# Location filter
location_filter = st.radio("Filter Games:", ["All", "Home", "Away"], index=0)

# Select an opponent for PRA comparison
opponent_name = st.selectbox("Select opponent team for PRA analysis:", ["Lakers", "Warriors", "Celtics", "Bucks", "Nuggets"])

# Fetch Data
df = get_game_logs(player_name, last_n_games=15, location_filter=location_filter)
matchup_df = get_game_logs_vs_team(player_name, opponent_name, ["2024-25", "2023-24", "2022-23"])

# Show DataFrame
if df is not None:
    st.dataframe(df[['GAME_DATE', 'MATCHUP', 'LOCATION', 'OPPONENT', 'PTS', 'REB', 'AST']])

# Plot Graphs
plot_combined_graphs(df, matchup_df, player_name, opponent_name)
