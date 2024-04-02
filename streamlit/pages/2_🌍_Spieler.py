import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer, FactAppearance, DimClub, DimCompetition, DimGame
import pandas as pd

# Verbindung zur Datenbank herstellen
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Cache für Metrik-Perzentile
metric_percentiles_cache = {}

def calculate_metric_per_90(player_id, column):
    value = session.query(
        func.sum(getattr(FactAppearance, column)) / func.sum(FactAppearance.minutes_played) * 90
    ).filter(FactAppearance.player_id == player_id).scalar()
    return float(value) if value is not None else 0

def calculate_weighted_percentile(player_id, columns, weights, position, metric):
    cache_key = f"{player_id}_{position}_{metric}"
    if cache_key in metric_percentiles_cache:
        return metric_percentiles_cache[cache_key]

    player_values = [calculate_metric_per_90(player_id, column) for column in columns]
    weighted_player_value = sum(value * weight for value, weight in zip(player_values, weights))

    all_players = session.query(DimPlayer.player_id).join(FactAppearance).filter(DimPlayer.position == position).distinct().all()
    all_player_ids = [player[0] for player in all_players]

    all_weighted_values = []
    for player_id in all_player_ids:
        player_values = [calculate_metric_per_90(player_id, column) for column in columns]
        weighted_value = sum(value * weight for value, weight in zip(player_values, weights))
        all_weighted_values.append(weighted_value)

    sorted_values = sorted(all_weighted_values)
    percentile = (sorted_values.index(weighted_player_value) + 1) / len(sorted_values) * 100

    metric_percentiles_cache[cache_key] = percentile
    return percentile

def calculate_metrics(player_id, position):
    metrics = {
        "Offensive": {
            "columns": ["goals2", "shots", "shots_on_target", "expected_goals", "assists", "expected_goal_assists"],
            "weights": [0.3, 0.2, 0.2, 0.1, 0.1, 0.1]
        },
        "Defensive": {
            "columns": ["number_of_tackles", "ball_win", "blocks", "touches"],
            "weights": [0.4, 0.3, 0.2, 0.1]
        },
        "Passing": {
            "columns": ["successful_passes", "attempted_passes", "pass_accuracy_in_percent", "progressive_passes"],
            "weights": [0.3, 0.2, 0.3, 0.2]
        },
        "Dribbling": {
            "columns": ["attempted_dribbles", "successful_dribbling", "progressive_runs"],
            "weights": [0.4, 0.4, 0.2]
        },
        "Discipline": {
            "columns": ["yellow_card", "red_card"],
            "weights": [0.7, 0.3]
        }
    }

    metric_percentiles = {}
    for metric, data in metrics.items():
        columns = data["columns"]
        weights = data["weights"]
        percentile = calculate_weighted_percentile(player_id, columns, weights, position, metric)
        metric_percentiles[metric] = percentile

    return metric_percentiles

def main():
    st.set_page_config(page_title='Fußballspieler-Analyse', layout='wide')
    st.title("Spielerauswertung")

    # Spalten für Spielerauswahl, Leerraum und Bilder erstellen
    select_col, empty_col, images_col = st.columns([2, 2, 1.5])

    # Dropdown-Menü für die Auswahl des Spielers in der ersten Spalte
    with select_col:
        players = session.query(DimPlayer).all()
        player_names = [player.name for player in players]
        selected_player_name = st.selectbox("Wähle einen Spieler", player_names)

    # Spieler anhand des ausgewählten Namens abrufen
    selected_player = session.query(DimPlayer).filter(DimPlayer.name == selected_player_name).first()

    if selected_player:
        # Spielerbild und Vereinswappen nebeneinander in der dritten Spalte anzeigen
        with images_col:
            player_col, club_col = st.columns(2)
            with player_col:
                st.image(selected_player.image_url, width=100)
            with club_col:
                current_club = session.query(DimClub).filter(DimClub.club_id == selected_player.current_club_id).first()
                if current_club:
                    club_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{current_club.club_id}.png?lm=1656580823"
                    st.image(club_logo_url, width=100)

        st.header(f'Spieleranalyse für {selected_player.name}')

        # Spielerinformationen horizontal anzeigen
        st.subheader('Spielerinformationen')
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Position', selected_player.position)
        col2.metric('Aktueller Verein', selected_player.current_club_name)
        col3.metric('Nationalität', selected_player.country_of_citizenship)
        col4.metric('Alter', pd.to_datetime('today').year - pd.to_datetime(selected_player.date_of_birth).year)

        # Vereinsinformationen horizontal anzeigen
        if current_club:
            st.subheader('Verein')
            col1, col2, col3 = st.columns(3)
            col1.metric('Verein', current_club.name)
            col2.metric('Stadium', current_club.stadium_name)
            col3.metric('Trainer', current_club.coach_name)

        # Gesamtstatistiken des Spielers abrufen
        total_goals = session.query(func.sum(FactAppearance.goals2)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_assists = session.query(func.sum(FactAppearance.assists)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_yellow_cards = session.query(func.sum(FactAppearance.yellow_card)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_red_cards = session.query(func.sum(FactAppearance.red_card)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(FactAppearance.player_id == selected_player.player_id,FactAppearance.goals2 != None).scalar()

        # Gesamtstatistiken anzeigen
        st.subheader('Gesamtstatistiken')
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric('Tore', int(total_goals) if total_goals is not None else 0)
        col2.metric('Vorlagen', int(total_assists) if total_assists is not None else 0)
        col3.metric('Gelbe Karten', int(total_yellow_cards) if total_yellow_cards is not None else 0)
        col4.metric('Rote Karten', int(total_red_cards) if total_red_cards is not None else 0)
        col5.metric('Spielminuten', int(total_minutes_played) if total_minutes_played is not None else 0)
        
        # Berechne die Metrik-Perzentile für den ausgewählten Spieler
        metric_percentiles = calculate_metrics(selected_player.player_id, selected_player.position)

        # Berechne den Overall-Wert als gewichteten Durchschnitt der Metrik-Perzentile
        overall_weights = {
            "Offensive": 0.3,
            "Defensive": 0.2,
            "Passing": 0.2,
            "Dribbling": 0.2,
            "Discipline": 0.1
        }
        metric_percentiles["Overall"] = sum(metric_percentiles[metric] * overall_weights[metric] for metric in metric_percentiles)

        # Metrik-Perzentile anzeigen
        st.subheader('Metrik-Perzentile')
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric('Offensive', f"{metric_percentiles['Offensive']:.2f}")
        col2.metric('Defensive', f"{metric_percentiles['Defensive']:.2f}")
        col3.metric('Passing', f"{metric_percentiles['Passing']:.2f}")
        col4.metric('Dribbling', f"{metric_percentiles['Dribbling']:.2f}")
        col5.metric('Discipline', f"{metric_percentiles['Discipline']:.2f}")
        col6.metric('Overall', f"{metric_percentiles['Overall']:.2f}")

    else:
        st.warning('Spieler nicht gefunden.')

if __name__ == '__main__':
    main()