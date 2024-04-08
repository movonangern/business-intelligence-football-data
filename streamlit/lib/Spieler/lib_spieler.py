#streamlit\lib\Spieler\lib_spieler.py

import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer, FactAppearance, DimGame, DimClub
import pandas as pd
import plotly.graph_objs as go
import joblib
import os
from ENV import DATABASE_URL

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

    if value is None:
        return None

    value = max(min(value, max_value), min_value)
    return (value - min_value) / (max_value - min_value)

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

def player_market_value_prediction(player_id):
    # Absoluten Pfad zur Modelldatei ermitteln
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'market_value_model.pkl')
    
    # Vortrainiertes Modell laden
    model = joblib.load(model_path)
    
    # Daten aus der Datenbank abrufen
    player = session.query(DimPlayer).filter(DimPlayer.player_id == player_id).first()
    appearances = session.query(FactAppearance).filter(FactAppearance.player_id == player_id).all()

    if not player or not appearances:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="Nicht genügend Daten für die Marktwertvorhersage", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return None, empty_fig, None, None, None, None, None

    # Daten in ein DataFrame umwandeln
    data = {
        'age': [player_age(player.date_of_birth)],
        'contract_days_remaining': [(pd.to_datetime(player.contract_expiration_date) - pd.Timestamp.now()).days if player.contract_expiration_date else None],
        'position': [player.position],
        'foot': [player.foot],
        'height_in_cm': [player.height_in_cm],
        'country_of_citizenship': [player.country_of_citizenship],
        'current_club_name': [player.current_club_name],
        'assists_per_game': [sum(a.assists or 0 for a in appearances) / len(appearances)],
        'minutes_played_per_game': [sum(a.minutes_played or 0 for a in appearances) / len(appearances)],
        'goals_per_game': [sum(a.goals2 or 0 for a in appearances) / len(appearances)],
        'shots_per_game': [sum(a.shots or 0 for a in appearances) / len(appearances)],
        'shots_on_target_per_game': [sum(a.shots_on_target or 0 for a in appearances) / len(appearances)],
        'yellow_cards_per_game': [sum(a.yellow_card or 0 for a in appearances) / len(appearances)],
        'red_cards_per_game': [sum(a.red_card or 0 for a in appearances) / len(appearances)],
        'successful_passes_per_game': [sum(a.successful_passes or 0 for a in appearances) / len(appearances)],
        'attempted_passes_per_game': [sum(a.attempted_passes or 0 for a in appearances) / len(appearances)],
        'progressive_passes_per_game': [sum(a.progressive_passes or 0 for a in appearances) / len(appearances)],
        'carries_per_game': [sum(a.carries or 0 for a in appearances) / len(appearances)],
        'progressive_runs_per_game': [sum(a.progressive_runs or 0 for a in appearances) / len(appearances)],
        'successful_dribbles_per_game': [sum(a.successful_dribbling or 0 for a in appearances) / len(appearances)],
        'attempted_dribbles_per_game': [sum(a.attempted_dribbles or 0 for a in appearances) / len(appearances)],
    }

    current_club = session.query(DimClub).filter(DimClub.club_id == player.current_club_id).first()
    if current_club:
        data['current_club_total_market_value'] = [current_club.total_market_value]
        data['current_club_squad_size'] = [current_club.squad_size]
        data['current_club_average_age'] = [current_club.average_age]
        data['current_club_foreigners_number'] = [current_club.foreigners_number]
        data['current_club_foreigners_percentage'] = [current_club.foreigners_percentage]
        data['current_club_national_team_players'] = [current_club.national_team_players]
        data['current_club_stadium_seats'] = [current_club.stadium_seats]
    else:
        data['current_club_total_market_value'] = [0]
        data['current_club_squad_size'] = [0]
        data['current_club_average_age'] = [0]
        data['current_club_foreigners_number'] = [0]
        data['current_club_foreigners_percentage'] = [0]
        data['current_club_national_team_players'] = [0]
        data['current_club_stadium_seats'] = [0]

    player_stats = pd.DataFrame(data)

    # Überprüfen, ob player_stats leer ist
    if player_stats.empty:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="Nicht genügend Daten für die Marktwertvorhersage", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return None, empty_fig, None, None, None, None, None

    # Marktwert des Spielers vorhersagen
    predicted_market_value = model.predict(player_stats)[0]

    # Feature Importance berechnen
    importances = model.named_steps['regressor'].feature_importances_
    feature_names = model.named_steps['preprocessor'].get_feature_names_out()
    feature_importances = pd.Series(importances, index=feature_names).sort_values(ascending=False)

    # Ergebnisse visualisieren
    actual_market_value = player.market_value_in_eur
    fig = go.Figure(data=[
        go.Bar(name='Tatsächlicher Marktwert', x=['Marktwert'], y=[actual_market_value]),
        go.Bar(name='Vorhergesagter Marktwert', x=['Marktwert'], y=[predicted_market_value])
    ])
    fig.update_layout(title=f'Marktwertvorhersage für {player.name}', xaxis_title='', yaxis_title='Marktwert (€)')
    
    # Hartcodierte Werte
    r2_score = 0.65
    mae = 4842088.85
    mse = 99719902216720.08
    rmse = 9985985.29
    
    return predicted_market_value, fig, r2_score, mae, mse, rmse, feature_importances

def get_player_stats(player_id):
    player = session.query(DimPlayer).filter(DimPlayer.player_id == player_id).first()
    
    if player:
        return {
            'goal_contribution': player.goal_contribution or 0,
            'defensive_contribution': player.defensive_contribution or 0,
            'passing_efficiency': player.passing_efficiency or 0,
            'dribbling_ability': player.dribbling_ability or 0,
            'shot_efficiency': player.shot_efficiency or 0,
            'discipline': player.discipline or 0,
            'involvement': player.involvement or 0,
            'overall_rating': player.overall_rating or 0
        }
    else:
        return {
            'goal_contribution': 0,
            'defensive_contribution': 0,
            'passing_efficiency': 0,
            'dribbling_ability': 0,
            'shot_efficiency': 0,
            'discipline': 0,
            'involvement': 0,
            'overall_rating': 0
        }
        
def create_playing_time_pie_chart(player_id):
    total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(
        FactAppearance.player_id == player_id,
        FactAppearance.player_current_club_id == FactAppearance.player_club_id,
        FactAppearance.minutes_played.isnot(None)
    ).scalar()

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

    # Wenn keine Daten vorhanden sind, werden Standardwerte verwendet
    if not values or sum(values) == 0:
        values = [33.3, 33.3, 33.3]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig.update_layout(showlegend=True)  # Legende anzeigen

    return fig

def get_total_stats(player_id):
    appearances = session.query(FactAppearance).filter(FactAppearance.player_id == player_id).all()
    
    total_goals = sum(a.goals2 or 0 for a in appearances)
    total_assists = sum(a.assists or 0 for a in appearances)
    total_yellow_cards = sum(a.yellow_card or 0 for a in appearances)
    total_red_cards = sum(a.red_card or 0 for a in appearances)
    total_minutes_played = sum(a.minutes_played or 0 for a in appearances)
    
    return total_goals, total_assists, total_yellow_cards, total_red_cards, total_minutes_played

def display_player_info(player, player_stats):
    st.header(f'Spieleranalyse für {player.name}')
    st.subheader('Spielerinformationen')

    col1, col2, col3 = st.columns(3)
    col1.metric('Position', player.position)
    col2.metric('Aktueller Verein', player.current_club_name)
    col3.metric('Nationalität', player.country_of_citizenship)

    col4, col5, col6 = st.columns(3)
    col4.metric('Alter', player_age(player.date_of_birth))
    col5.metric('Marktwert', f"{player.market_value_in_eur:,.0f} €")
    col6.metric('Berater', player.agent_name)
    
    total_goals, total_assists, total_yellow_cards, total_red_cards, total_minutes_played = get_total_stats(player.player_id)
    
    st.subheader('Gesamtstatistiken')
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric('Tore', int(total_goals))
    col2.metric('Vorlagen', int(total_assists))
    col3.metric('Gelbe Karten', int(total_yellow_cards))
    col4.metric('Rote Karten', int(total_red_cards))
    col5.metric('Spielminuten', int(total_minutes_played))
    
    st.subheader('Metriken')
    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Overall Rating']
    metrics = [player_stats['goal_contribution'], player_stats['defensive_contribution'], player_stats['passing_efficiency'], player_stats['dribbling_ability'], player_stats['shot_efficiency'], player_stats['discipline'], player_stats['involvement'], player_stats['overall_rating']]
    metric_descriptions = [
        "Tore + 0,5 x Vorlagen pro 90 Minuten",
        "Tackles + 0,5 x Blocks pro 90 Minuten",
        "Erfolgreiche Pässe im Verhältnis zu allen gespielten Pässen",
        "Erfolgreiche Dribblings im Verhältnis zu allen Dribbling-Versuchen",
        "Schüsse aufs Tor im Verhältnis zu allen Schüssen",
        "1 - (5 x Gelbe Karten + 15 x Rote Karten) pro 90 Minuten",
        "Ballkontakte + Ballführungen pro 90 Minuten",
        "Durchschnitt aller Metriken"
    ]
    for i in range(0, len(metrics), 4):
        cols = st.columns(4)
        for col, metric, label, description in zip(cols, metrics[i:i+4], metric_labels[i:i+4], metric_descriptions[i:i+4]):
            if metric is not None:
                col.metric(label, f"{metric:.2f}", help=description)
            else:
                col.metric(label, "-", help=description)
    
    empty_col = st.columns(1)
    
    # Radar-Diagramm und Spielzeit-Aufteilung in zwei Spalten
    radar_col, pie_col = st.columns(2)

    with radar_col:
        radar_fig = create_radar_chart(metrics, metric_labels, player.name)
        st.subheader('Radar-Diagramm')
        st.plotly_chart(radar_fig, use_container_width=True)

    with pie_col:
        playing_time_chart = create_playing_time_pie_chart(player.player_id)
        if playing_time_chart:
            st.subheader('Spielzeit Aufteilung')
            st.plotly_chart(playing_time_chart, use_container_width=True)

def compare_players(player1_id, player2_id):
    player1 = session.query(DimPlayer).filter(DimPlayer.player_id == player1_id).first()
    player2 = session.query(DimPlayer).filter(DimPlayer.player_id == player2_id).first()

    player1_stats = get_player_stats(player1_id)
    player2_stats = get_player_stats(player2_id)

    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Overll Rating']
    player1_metrics = [player1_stats['goal_contribution'], player1_stats['defensive_contribution'], player1_stats['passing_efficiency'], player1_stats['dribbling_ability'], player1_stats['shot_efficiency'], player1_stats['discipline'], player1_stats['involvement'], player1_stats['overall_rating']]
    player2_metrics = [player2_stats['goal_contribution'], player2_stats['defensive_contribution'], player2_stats['passing_efficiency'], player2_stats['dribbling_ability'], player2_stats['shot_efficiency'], player2_stats['discipline'], player2_stats['involvement'], player2_stats['overall_rating']]

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
    metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Overall Rating']
    
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