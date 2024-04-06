#streamlit\pages\2_🌍_Spieler.py

import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer, DimClub
from lib.Spieler.lib_spieler import get_player_stats, display_player_info, player_age, compare_players, player_market_value_prediction


DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

            
def main():
    st.set_page_config(page_title='Fußballspieler-Analyse', layout='wide')
    st.title("Spielerauswertung")
    
    tab1, tab2 = st.tabs(["Einzelspieleranalyse", "Spielervergleich"])
    
    with tab1:
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
            
            player_stats = get_player_stats(selected_player.player_id)
            display_player_info(selected_player, player_stats)
        
            predicted_market_value, fig, r2, mae, mse, rmse, feature_importances = player_market_value_prediction(selected_player.player_id)

            if predicted_market_value is not None:
                st.subheader('Marktwertvorhersage')
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.write(f"### Vorhergesagter Marktwert: {predicted_market_value:,.0f} €")
                    st.write(f"R²-Score: {r2:.2f}")
                    st.write(f"Mittlerer absoluter Fehler (MAE): {mae:,.0f} €")
                    st.write(f"Mittlerer quadratischer Fehler (MSE): {mse:,.0f} €")
                    st.write(f"Wurzel aus dem mittleren quadratischen Fehler (RMSE): {rmse:,.0f} €")

            else:
                st.warning('Für diesen Spieler ist keine Marktwertvorhersage möglich, da keine Leistungsdaten vorliegen.')
            
        else:
            st.warning('Spieler nicht gefunden.')

    with tab2:
        st.subheader('Spielervergleich (H2H)')
        player1_col, player2_col = st.columns([3, 3])
        players = session.query(DimPlayer).all()

        with player1_col:
            player1_image_col, player1_club_col, empty_col, player1_name_col = st.columns([1, 1, 1, 3])
            player1_name = player1_name_col.selectbox("Wähle Spieler 1", [player.name for player in players], key="player1")
            player1 = session.query(DimPlayer).filter(DimPlayer.name == player1_name).first()
            if player1:
                player1_image_col.image(player1.image_url, width=75)
                player1_club = session.query(DimClub).filter(DimClub.club_id == player1.current_club_id).first()
                if player1_club:
                    club1_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{player1_club.club_id}.png?lm=1656580823"
                    player1_club_col.image(club1_logo_url, width=75)
                
                player1_info_col1, player1_info_col2 = st.columns(2)
                player1_info_col1.metric('Alter', player_age(player1.date_of_birth))
                player1_info_col2.metric('Position', player1.position)

        with player2_col:
            player2_name_col, empty_col, player2_image_col, player2_club_col = st.columns([3, 1, 1, 1])
            player2_name = player2_name_col.selectbox("Wähle Spieler 2", [player.name for player in players], key="player2")
            player2 = session.query(DimPlayer).filter(DimPlayer.name == player2_name).first()
            if player2:
                player2_image_col.image(player2.image_url, width=75)
                player2_club = session.query(DimClub).filter(DimClub.club_id == player2.current_club_id).first()
                if player2_club:
                    club2_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{player2_club.club_id}.png?lm=1656580823"
                    player2_club_col.image(club2_logo_url, width=75)
                
                player2_info_col1, player2_info_col2 = st.columns(2)
                player2_info_col1.metric('Alter', player_age(player2.date_of_birth))
                player2_info_col2.metric('Position', player2.position)

        if player1 and player2:
            _, chart_col, _ = st.columns([1.75, 8, 1])  # Hier wurde die Zahl auf 8 geändert
            with chart_col:
                comparison_fig, player1_stats, player2_stats = compare_players(player1.player_id, player2.player_id)
                st.plotly_chart(comparison_fig, use_container_width=True)

            metric_labels = ['Goal Contribution', 'Defensive Contribution', 'Passing Efficiency', 'Dribbling Ability', 'Shot Efficiency', 'Discipline', 'Involvement', 'Overall Performance']

            player1_name_col, metric_cols, player2_name_col = st.columns([2, 4, 2])
            player1_name_col.markdown(f"<h3 style='text-align: center;'>{player1.name}</h3>", unsafe_allow_html=True)
            player2_name_col.markdown(f"<h3 style='text-align: center;'>{player2.name}</h3>", unsafe_allow_html=True)

            for metric, player1_value, player2_value in zip(metric_labels, player1_stats, player2_stats):
                player1_metric_col, metric_label_col, player2_metric_col = metric_cols.columns([2, 2, 2])

                if player1_value is not None and player2_value is not None:
                    if player1_value > player2_value:
                        player1_metric_col.markdown(f"""
                        <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #155724; font-size: 20px; font-weight: bold; margin: 0;">{player1_value:.2f} <span style="color: green;">+{player1_value - player2_value:.2f}</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                        player2_metric_col.markdown(f"""
                        <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #721c24; font-size: 20px; font-weight: bold; margin: 0;">{player2_value:.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif player2_value > player1_value:
                        player1_metric_col.markdown(f"""
                        <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #721c24; font-size: 20px; font-weight: bold; margin: 0;">{player1_value:.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        player2_metric_col.markdown(f"""
                        <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #155724; font-size: 20px; font-weight: bold; margin: 0;">{player2_value:.2f} <span style="color: green;">+{player2_value - player1_value:.2f}</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        player1_metric_col.markdown(f"""
                        <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">{player1_value:.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        player2_metric_col.markdown(f"""
                        <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">{player2_value:.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    player1_metric_col.markdown(f"""
                    <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                        <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">-</p>
                    </div>
                    """, unsafe_allow_html=True)
                    player2_metric_col.markdown(f"""
                    <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                        <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">-</p>
                    </div>
                    """, unsafe_allow_html=True)

                metric_label_col.markdown(f"<p style='text-align: center; font-weight: bold;'>{metric}</p>", unsafe_allow_html=True)

        else:
            st.warning('Einer oder beide Spieler nicht gefunden.')

if __name__ == '__main__':
   main()