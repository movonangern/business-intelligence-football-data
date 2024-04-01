import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from utils.ORM_model import DimPlayer, FactAppearance, DimClub, DimCompetition, DimGame
import pandas as pd
import plotly.express as px
from sqlalchemy import Integer, Float, Numeric

# Verbindung zur Datenbank herstellen
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def calculate_metrics(player_id, player_position):
    # Metriken und Gewichtungen definieren
    metrics = {
        'Offensive': {'goals2': 0.4, 'assists': 0.3, 'shots': 0.1, 'shots_on_target': 0.2, 'expected_goals': 0.1, 'expected_goal_assists': 0.1},
        'Defensive': {'number_of_tackles': 0.4, 'ball_win': 0.4, 'blocks': 0.2},
        'Passing': {'successful_passes': 0.3, 'attempted_passes': 0.2, 'pass_accuracy_in_percent': 0.3, 'progressive_passes': 0.2},
        'Dribbling': {'carries': 0.4, 'progressive_runs': 0.3, 'attempted_dribbles': 0.2, 'successful_dribbling': 0.1},
        'Discipline': {'yellow_cards': 0.5, 'red_cards': 0.5}
    }

    # Metriken berechnen
    metric_values = {}
    for metric_name, columns in metrics.items():
        metric_value = 0
        for column, weight in columns.items():
            percentile = session.query(
                func.percent_rank().over(
                    order_by=getattr(FactAppearance, column),
                    partition_by=DimPlayer.position
                )
            ).filter(
                FactAppearance.player_id == player_id,
                DimPlayer.position == player_position
            ).join(
                DimPlayer, FactAppearance.player_id == DimPlayer.player_id
            ).scalar()

            if percentile is not None:
                metric_value += weight * percentile * 100
        
        metric_values[metric_name] = round(metric_value, 2)

    # Allgemeine Metrik berechnen
    all_columns = [col.name for col in FactAppearance.__table__.columns if isinstance(col.type, (Integer, Float, Numeric))]
    all_values = []
    for col in all_columns:
        percentile = session.query(
            func.percent_rank().over(
                order_by=getattr(FactAppearance, col),
                partition_by=DimPlayer.position
            )
        ).filter(
            FactAppearance.player_id == player_id,
            DimPlayer.position == player_position
        ).join(
            DimPlayer, FactAppearance.player_id == DimPlayer.player_id
        ).scalar()

        if percentile is not None:
            all_values.append(percentile * 100)
    
    if len(all_values) > 0:
        overall_metric = round(sum(all_values) / len(all_values), 2)
    else:
        overall_metric = 0
    
    metric_values['Overall'] = overall_metric

    return metric_values

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
        total_yellow_cards = session.query(func.sum(FactAppearance.yellow_cards)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_red_cards = session.query(func.sum(FactAppearance.red_cards)).filter(FactAppearance.player_id == selected_player.player_id).scalar()
        total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(FactAppearance.player_id == selected_player.player_id).scalar()

        # Gesamtstatistiken anzeigen
        st.subheader('Gesamtstatistiken')
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric('Tore', int(total_goals) if total_goals is not None else 0)
        col2.metric('Vorlagen', int(total_assists) if total_assists is not None else 0)
        col3.metric('Gelbe Karten', int(total_yellow_cards) if total_yellow_cards is not None else 0)
        col4.metric('Rote Karten', int(total_red_cards) if total_red_cards is not None else 0)
        col5.metric('Spielminuten', int(total_minutes_played) if total_minutes_played is not None else 0)

        # Metriken berechnen und anzeigen
        player_metrics = calculate_metrics(selected_player.player_id, selected_player.position)
        st.subheader('Metriken')
        col1, col2, col3 = st.columns(3)
        col1.metric('Offensive', float(player_metrics['Offensive']))
        col2.metric('Defensive', float(player_metrics['Defensive']))
        col3.metric('Passing', float(player_metrics['Passing']))
        col1.metric('Dribbling', float(player_metrics['Dribbling']))
        col2.metric('Discipline', float(player_metrics['Discipline']))
        col3.metric('Overall', float(player_metrics['Overall']))
    else:
        st.warning('Spieler nicht gefunden.')

if __name__ == '__main__':
    main()