import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from nba_api.stats.endpoints import PlayerGameLog
from nba_api.stats.static import players
import datetime
import numpy as np
from sklearn.linear_model import LinearRegression

# Retrieve player ID
def get_player_id(player_name):
    player_list = players.get_players()
    for player in player_list:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    return None

# Fetch player game logs
def get_game_logs(player_name, seasons, date_range):
    player_id = get_player_id(player_name)
    if not player_id:
        st.warning(f"⚠️ Player '{player_name}' not found! Check the name.")
        return None

    all_logs = []
    for season in seasons:
        gamelog = PlayerGameLog(player_id=player_id, season=season)
        df = gamelog.get_data_frames()[0]
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        
        # Filter by date range
        df = df[(df["GAME_DATE"] >= pd.to_datetime(date_range[0])) & 
                (df["GAME_DATE"] <= pd.to_datetime(date_range[1]))]
        
        all_logs.append(df)

    return pd.concat(all_logs, ignore_index=True) if all_logs else None

# Predict Points using Linear Regression
def predict_points(df):
    if df is None or df.empty:
        return None
    df = df.sort_values("GAME_DATE")
    df["Game_Number"] = np.arange(len(df))  # Create a numerical feature

    X = df[["Game_Number"]]
    y = df["PTS"]

    model = LinearRegression().fit(X, y)
    next_game = np.array([[len(df) + 1]])
    predicted_pts = model.predict(next_game)[0]

    return round(predicted_pts, 1)

# Visualization
def plot_comparison_graphs(df1, df2, player_name1, player_name2):
    fig = make_subplots(
        rows=1, cols=3, 
        subplot_titles=[
            f"{player_name1} vs. {player_name2} - Points (PTS)",
            f"{player_name1} vs. {player_name2} - Rebounds (REB)",
            f"{player_name1} vs. {player_name2} - Assists (AST)"
        ],
        horizontal_spacing=0.12
    )

    if df1 is not None and df2 is not None:
        df1["Game Date"] = df1["GAME_DATE"].dt.strftime('%b %d')
        df2["Game Date"] = df2["GAME_DATE"].dt.strftime('%b %d')

        # Points comparison
        fig.add_trace(go.Bar(x=df1["Game Date"], y=df1["PTS"], name=f"{player_name1} PTS", marker=dict(color="blue")), row=1, col=1)
        fig.add_trace(go.Bar(x=df2["Game Date"], y=df2["PTS"], name=f"{player_name2} PTS", marker=dict(color="red")), row=1, col=1)

        # Rebounds comparison
        fig.add_trace(go.Bar(x=df1["Game Date"], y=df1["REB"], name=f"{player_name1} REB", marker=dict(color="blue")), row=1, col=2)
        fig.add_trace(go.Bar(x=df2["Game Date"], y=df2["REB"], name=f"{player_name2} REB", marker=dict(color="red")), row=1, col=2)

        # Assists comparison
        fig.add_trace(go.Bar(x=df1["Game Date"], y=df1["AST"], name=f"{player_name1} AST", marker=dict(color="blue")), row=1, col=3)
        fig.add_trace(go.Bar(x=df2["Game Date"], y=df2["AST"], name=f"{player_name2} AST", marker=dict(color="red")), row=1, col=3)

    fig.update_layout(title_text=f"{player_name1} vs. {player_name2} Performance Comparison", template="plotly_dark", height=600, width=1200)
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig)

# Streamlit UI
st.title("🏀 NBA Player Comparison & Performance Dashboard")

# Sidebar filters
st.sidebar.header("🔍 Filters")
seasons = ["2024-25", "2023-24", "2022-23", "2021-22"]
selected_seasons = st.sidebar.multiselect("Select Seasons:", seasons, default=seasons[:2])

date_range = st.sidebar.date_input("Select Date Range:", 
                                   [datetime.date(2024, 1, 1), datetime.date.today()])

# Get player inputs
player_name1 = st.text_input("Enter first player name:", "LeBron James")
player_name2 = st.text_input("Enter second player name (optional):", "")

# Fetch Data
df1 = get_game_logs(player_name1, selected_seasons, date_range)
df2 = get_game_logs(player_name2, selected_seasons, date_range) if player_name2 else None

# Predict next game points
predicted_pts1 = predict_points(df1)
predicted_pts2 = predict_points(df2) if df2 is not None else None

# Display Metrics
st.header(f"📊 {player_name1} Performance Metrics")
if predicted_pts1:
    st.metric(label="🔮 Predicted Next Game Points", value=predicted_pts1)

if df1 is not None:
    st.subheader(f"📊 Last {len(df1)} Games - {player_name1}")
    st.dataframe(df1[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST"]])

if player_name2:
    st.header(f"📊 {player_name2} Performance Metrics")
    if predicted_pts2:
        st.metric(label="🔮 Predicted Next Game Points", value=predicted_pts2)

    if df2 is not None:
        st.subheader(f"📊 Last {len(df2)} Games - {player_name2}")
        st.dataframe(df2[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST"]])

# Plot Comparison Graphs
if df1 is not None and df2 is not None:
    plot_comparison_graphs(df1, df2, player_name1, player_name2)
