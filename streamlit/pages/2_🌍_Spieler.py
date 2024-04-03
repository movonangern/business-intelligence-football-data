import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer, FactAppearance, DimClub
import pandas as pd
import numpy as np

DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def calculate_metric(metric_values, max_value):
    if max_value:
        valid_values = [sum(values) for values in metric_values if all(value is not None for value in values)]
        return np.mean([value / max_value * 100 for value in valid_values]) if valid_values else 0
    return 0

def calculate_discipline(yellow_card, red_card, max_value):
    if all(v is not None for v in [yellow_card, red_card, max_value]) and max_value != 0:
        return 100 - ((yellow_card + red_card) / max_value * 100)
    return 100

def player_age(date_of_birth):
    return pd.to_datetime('today').year - pd.to_datetime(date_of_birth).year

def main():
    st.set_page_config(page_title='Fußballspieler-Analyse', layout='wide')
    st.title("Spielerauswertung")
    select_col, _, images_col = st.columns([2, 2, 1.5])

    with select_col:
        players = session.query(DimPlayer).all()
        selected_player_name = st.selectbox("Wähle einen Spieler", [player.name for player in players])

    selected_player = session.query(DimPlayer).filter(DimPlayer.name == selected_player_name).first()

    if selected_player:
        current_club = session.query(DimClub).filter(DimClub.club_id == selected_player.current_club_id).first()

        with images_col:
            player_col, club_col = st.columns(2)
            player_col.image(selected_player.image_url, width=100)
            if current_club:
                club_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{current_club.club_id}.png?lm=1656580823"
                club_col.image(club_logo_url, width=100)

        st.header(f'Spieleranalyse für {selected_player.name}')

        st.subheader('Spielerinformationen')
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Position', selected_player.position)
        col2.metric('Aktueller Verein', selected_player.current_club_name)
        col3.metric('Nationalität', selected_player.country_of_citizenship)
        col4.metric('Alter', player_age(selected_player.date_of_birth))

        if current_club:
            st.subheader('Verein')
            col1, col2, col3 = st.columns(3)
            col1.metric('Verein', current_club.name)
            col2.metric('Stadium', current_club.stadium_name)
            col3.metric('Trainer', current_club.coach_name)

        total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(FactAppearance.player_id == selected_player.player_id, FactAppearance.goals2 != None).scalar()
        total_stats = session.query(func.sum(FactAppearance.goals2), func.sum(FactAppearance.assists), func.sum(FactAppearance.yellow_card), func.sum(FactAppearance.red_card)).filter(FactAppearance.player_id == selected_player.player_id).first()

        st.subheader('Gesamtstatistiken')
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric('Tore', int(total_stats[0]) if total_stats[0] else 0)
        col2.metric('Vorlagen', int(total_stats[1]) if total_stats[1] else 0)
        col3.metric('Gelbe Karten', int(total_stats[2]) if total_stats[2] else 0)
        col4.metric('Rote Karten', int(total_stats[3]) if total_stats[3] else 0)
        col5.metric('Spielminuten', int(total_minutes_played) if total_minutes_played else 0)

        max_values = session.query(
            func.max(FactAppearance.goals1 + FactAppearance.assists + FactAppearance.expected_goals),
            func.max(FactAppearance.number_of_tackles + FactAppearance.blocks),
            func.max(FactAppearance.successful_passes + FactAppearance.progressive_passes + FactAppearance.pass_accuracy_in_percent),
            func.max(FactAppearance.attempted_dribbles + FactAppearance.successful_dribbling + FactAppearance.progressive_runs),
            func.max(FactAppearance.shots_on_target + FactAppearance.expected_goals),
            func.max(FactAppearance.yellow_card + FactAppearance.red_card),
            func.max(FactAppearance.touches + FactAppearance.carries + FactAppearance.attempted_passes),
            func.max(FactAppearance.converted_penalties + FactAppearance.attempted_penalty)
        ).first()

        appearances = session.query(FactAppearance).filter(FactAppearance.player_id == selected_player.player_id).all()
        metrics = [
            calculate_metric([(a.goals1, a.assists, a.expected_goals) for a in appearances], max_values[0]),
            calculate_metric([(a.number_of_tackles, a.blocks) for a in appearances], max_values[1]),
            calculate_metric([(a.successful_passes, a.progressive_passes, a.pass_accuracy_in_percent) for a in appearances], max_values[2]),
            calculate_metric([(a.attempted_dribbles, a.successful_dribbling, a.progressive_runs) for a in appearances], max_values[3]),
            calculate_metric([(a.shots_on_target, a.expected_goals) for a in appearances], max_values[4]),
            np.mean([calculate_discipline(a.yellow_card, a.red_card, max_values[5]) for a in appearances]),
            calculate_metric([(a.touches, a.carries, a.attempted_passes) for a in appearances], max_values[6]),
            calculate_metric([(a.converted_penalties, a.attempted_penalty) for a in appearances], max_values[7])
        ]

        st.subheader('Metriken')
        metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Penalty Contribution']
        for i in range(0, len(metrics), 4):
            cols = st.columns(4)
            for col, metric, label in zip(cols, metrics[i:i+4], metric_labels[i:i+4]):
                col.metric(label, f"{metric:.2f}%")
    else:
        st.warning('Spieler nicht gefunden.')

if __name__ == '__main__':
    main()
