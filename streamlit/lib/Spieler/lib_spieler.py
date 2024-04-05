#streamlit\lib\Spieler\lib_spieler.py

import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer, FactAppearance, DimGame
import pandas as pd
import plotly.graph_objs as go

DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def player_age(date_of_birth):
    today = pd.to_datetime('today')
    return today.year - pd.to_datetime(date_of_birth).year

def normalize_metric(value, min_value=None, max_value=None):
    if min_value is None:
        min_value = 0
    if max_value is None:
        max_value = 1
    return (value - min_value) / (max_value - min_value) if value is not None else None

def calculate_weighted_stat(appearances, stat_name, weight_factor):
    total_minutes_played = sum(a.minutes_played or 0 for a in appearances if a.minutes_played is not None)
    weighted_sum = sum(((getattr(a, stat_name, 0) or 0) * (a.minutes_played or 0) / 90) for a in appearances if a.minutes_played is not None and getattr(a, stat_name, None) is not None)
    return weighted_sum / (total_minutes_played / 90) * weight_factor if total_minutes_played else 0

def create_radar_chart(metrics, metric_labels, player_name):
    radar_data = [go.Scatterpolar(
        r=metrics,
        theta=metric_labels,
        fill='toself',
        name=player_name
    )]

    radar_layout = go.Layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1])
        ),
        showlegend=False
    )

    radar_fig = go.Figure(data=radar_data, layout=radar_layout)
    return radar_fig

def get_player_stats(player_id):
    appearances = session.query(FactAppearance).filter(FactAppearance.player_id == player_id).all()
    total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(FactAppearance.player_id == player_id, FactAppearance.goals2 != None).scalar()
    total_stats = session.query(func.sum(FactAppearance.goals2), func.sum(FactAppearance.assists), func.sum(FactAppearance.yellow_card), func.sum(FactAppearance.red_card)).filter(FactAppearance.player_id == player_id).first()

    # Gewichtete Statistiken berechnen
    goal_contribution = normalize_metric(calculate_weighted_stat(appearances, 'goals2', 1.0) + calculate_weighted_stat(appearances, 'assists', 0.5))
    defensive_contribution = normalize_metric(calculate_weighted_stat(appearances, 'number_of_tackles', 0.5) + calculate_weighted_stat(appearances, 'blocks', 0.5))
    passing_efficiency = normalize_metric(calculate_weighted_stat(appearances, 'successful_passes', 1.0) / (calculate_weighted_stat(appearances, 'attempted_passes', 1.0) or 1))
    dribbling_ability = normalize_metric(calculate_weighted_stat(appearances, 'successful_dribbling', 1.0) / (calculate_weighted_stat(appearances, 'attempted_dribbles', 1.0) or 1))
    shot_efficiency = normalize_metric(calculate_weighted_stat(appearances, 'shots_on_target', 1.0) / (calculate_weighted_stat(appearances, 'shots', 1.0) or 1))
    discipline = normalize_metric(1 - (calculate_weighted_stat(appearances, 'yellow_card', 5.0) + calculate_weighted_stat(appearances, 'red_card', 10.0)))
    involvement = normalize_metric(calculate_weighted_stat(appearances, 'touches', 1) + calculate_weighted_stat(appearances, 'carries', 1), 0, 200)
    penalty_contribution = normalize_metric(calculate_weighted_stat(appearances, 'converted_penalties', 1.0) / (calculate_weighted_stat(appearances, 'attempted_penalty', 1.0) or 1))

    return {
        'total_minutes_played': total_minutes_played,
        'total_stats': total_stats,
        'goal_contribution': goal_contribution,
        'defensive_contribution': defensive_contribution,
        'passing_efficiency': passing_efficiency,
        'dribbling_ability': dribbling_ability,
        'shot_efficiency': shot_efficiency,
        'discipline': discipline,
        'involvement': involvement,
        'penalty_contribution': penalty_contribution
    }

def create_playing_time_pie_chart(player_id):
    total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(
        FactAppearance.player_id == player_id,
        FactAppearance.player_current_club_id == FactAppearance.player_club_id,
        FactAppearance.minutes_played.isnot(None)
    ).scalar()

    if total_minutes_played is None:
        return None

    player = session.query(DimPlayer).filter(DimPlayer.player_id == player_id).first()
    current_club_id = player.current_club_id

    appearances = session.query(FactAppearance).filter(
        FactAppearance.player_id == player_id,
        FactAppearance.player_current_club_id == FactAppearance.player_club_id,
        FactAppearance.minutes_played.isnot(None)
    ).all()
    games_played = set(a.game_id for a in appearances)

    current_season = None
    if appearances:
        current_season = appearances[0].game.season if appearances[0].game else None

    club_games = session.query(DimGame.game_id).filter(
        DimGame.home_club_id == current_club_id,
        DimGame.season == current_season if current_season is not None else True
    ).union(
        session.query(DimGame.game_id).filter(
            DimGame.away_club_id == current_club_id,
            DimGame.season == current_season if current_season is not None else True
        )
    ).all()

    games_not_played = set(game_id for game_id, in club_games) - games_played

    start_minutes = sum(a.minutes_played for a in appearances if a.minutes_played >= 90)
    sub_minutes = sum(a.minutes_played for a in appearances if a.minutes_played < 90 and a.minutes_played > 0)
    not_played_minutes = sum(90 for game_id in games_not_played)

    labels = ['Startelf', 'Eingewechselt', 'Nicht gespielt']
    values = [start_minutes, sub_minutes, not_played_minutes]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig.update_layout(title_text='Spielzeit Aufteilung')

    return fig

def display_player_info(player, player_stats):
    st.header(f'Spieleranalyse für {player.name}')
    st.subheader('Spielerinformationen')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Position', player.position)
    col2.metric('Aktueller Verein', player.current_club_name)
    col3.metric('Nationalität', player.country_of_citizenship)
    col4.metric('Alter', player_age(player.date_of_birth))

    st.subheader('Gesamtstatistiken')
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric('Tore', int(player_stats['total_stats'][0]) if player_stats['total_stats'][0] else 0)
    col2.metric('Vorlagen', int(player_stats['total_stats'][1]) if player_stats['total_stats'][1] else 0)
    col3.metric('Gelbe Karten', int(player_stats['total_stats'][2]) if player_stats['total_stats'][2] else 0)
    col4.metric('Rote Karten', int(player_stats['total_stats'][3]) if player_stats['total_stats'][3] else 0)
    col5.metric('Spielminuten', int(player_stats['total_minutes_played']) if player_stats['total_minutes_played'] else 0)

    st.subheader('Metriken')
    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Penalty Contribution']
    metrics = [player_stats['goal_contribution'], player_stats['defensive_contribution'], player_stats['passing_efficiency'], player_stats['dribbling_ability'], player_stats['shot_efficiency'], player_stats['discipline'], player_stats['involvement'], player_stats['penalty_contribution']]
    metric_descriptions = [
        "Torbeteiligung (Tore + 0,5 x Vorlagen) pro 90 Minuten.",
        "Defensiver Beitrag (Tackles + 0,5 x Blocks) pro 90 Minuten.",
        "Erfolgreiche Pässe im Verhältnis zu allen gespielten Pässen.",
        "Erfolgreiche Dribblings im Verhältnis zu allen Dribbling-Versuchen.",
        "Schüsse aufs Tor im Verhältnis zu allen Schüssen.",
        "Disziplin (1 - (5 x Gelbe Karten + 15 x Rote Karten) pro 90 Minuten).",
        "Ballkontakte pro 90 Minuten.",
        "Erfolgreiche Elfmeter im Verhältnis zu allen geschossenen Elfmetern."
    ]
    for i in range(0, len(metrics), 4):
        cols = st.columns(4)
        for col, metric, label, description in zip(cols, metrics[i:i+4], metric_labels[i:i+4], metric_descriptions[i:i+4]):
            if metric is not None:
                col.metric(label, f"{metric:.2f}", description, delta_color="off")
            else:
                col.metric(label, "-", description, delta_color="off")

    # Radar-Diagramm erstellen
    radar_fig = create_radar_chart(metrics, metric_labels, player.name)
    st.subheader('Radar-Diagramm')
    st.plotly_chart(radar_fig)
    
    playing_time_chart = create_playing_time_pie_chart(player.player_id)
    if playing_time_chart:
        st.subheader('Spielzeit Aufteilung')
        st.plotly_chart(playing_time_chart)

def compare_players(player1_id, player2_id):
    player1 = session.query(DimPlayer).filter(DimPlayer.player_id == player1_id).first()
    player2 = session.query(DimPlayer).filter(DimPlayer.player_id == player2_id).first()

    player1_stats = get_player_stats(player1_id)
    player2_stats = get_player_stats(player2_id)

    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Penalty Contribution']
    player1_metrics = [player1_stats['goal_contribution'], player1_stats['defensive_contribution'], player1_stats['passing_efficiency'], player1_stats['dribbling_ability'], player1_stats['shot_efficiency'], player1_stats['discipline'], player1_stats['involvement'], player1_stats['penalty_contribution']]
    player2_metrics = [player2_stats['goal_contribution'], player2_stats['defensive_contribution'], player2_stats['passing_efficiency'], player2_stats['dribbling_ability'], player2_stats['shot_efficiency'], player2_stats['discipline'], player2_stats['involvement'], player2_stats['penalty_contribution']]

    radar_fig = go.Figure()
    radar_fig.add_trace(go.Scatterpolar(r=player1_metrics, theta=metric_labels, fill='toself', name=player1.name))
    radar_fig.add_trace(go.Scatterpolar(r=player2_metrics, theta=metric_labels, fill='toself', name=player2.name))

    radar_fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=dict(text=f"{player1.name} vs {player2.name}"),
        width=800, height=600  # Hier haben wir die Größe des Diagramms angepasst
    )

    return radar_fig, player1_metrics, player2_metrics

def display_comparison_metrics(player1_metrics, player2_metrics):
    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Penalty Contribution']
    
    data = {'Metric': metric_labels,
            'Player 1': player1_metrics,
            'Player 2': player2_metrics}
    
    df = pd.DataFrame(data)
    
    # Hervorhebung der besseren Werte
    def highlight_better(x):
        color = 'background-color: lightgreen' if x['Player 1'] > x['Player 2'] else 'background-color: lightcoral' if x['Player 1'] < x['Player 2'] else ''
        return [f'background-color: lightgray' if pd.isna(val) else color for val in x]
    
    df = df.style.apply(highlight_better, axis=1)
    
    st.dataframe(df)