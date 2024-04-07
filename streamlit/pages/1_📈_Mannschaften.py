#streamlit/pages/1_📈_Mannschaften.py

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimClub
import streamlit as st
from sqlalchemy.orm import sessionmaker
from lib.Mannschaften.lib_mannschaften import get_club_info, get_players_by_team, create_players_df, get_top_scorers, plot_top_scorers_bar, plot_points_over_season, plot_home_away_game_results_bar, plot_game_outcomes, display_team_comparison_metrics, compare_team_performance, evaluate_team_form, get_club_total_market_value, calculate_league_average_points, get_preferred_formation_by_team_name, get_selected_team_id

# Datenbankverbindung einrichten
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

    

def main():
    st.set_page_config(layout='wide')
    st.title("Mannschaftsauswertung")
    
    with Session() as session:
        teams = session.query(DimClub.name, DimClub.club_id).all()
        team_options = {name: club_id for name, club_id in teams}
        selected_team_name = st.selectbox("Wähle eine Mannschaft", options=list(team_options.keys()))

        tab1, tab2, = st.tabs(["Mannschaft", "H2H"])
        with tab1:
            if selected_team_name:
                selected_team_id = team_options[selected_team_name]
                club_info = get_club_info(session, selected_team_name)

                if club_info:
                    st.subheader(f"Vereinsinformationen für {selected_team_name}")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Kadergröße", str(club_info.squad_size))
                    
                    net_transfer_value = club_info.net_transfer_record.strip().replace('€', '').replace('m', ' Mio').replace('k', ' K').replace('+', '').replace('-', '')
                    if '-' in club_info.net_transfer_record:
                        col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Verlust", delta_color="inverse") 
                    else:
                        col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Gewinn", delta_color="normal")
                    
                    ### First ROW
                    col3.metric("Anteil Legionäre (%)", f"{float(club_info.foreigners_percentage)} %")
                    col4.metric("Durchschnittsalter", float(club_info.average_age))
                    total_market_value = get_club_total_market_value(session, selected_team_id)
                    formatted_market_value = '{:,.2f} Mio'.format(total_market_value / 1000000) if total_market_value >= 1000000 else '{:,.2f}'.format(total_market_value)
                    col5.metric("Teamwert", f"€ {formatted_market_value}")  
                    
                    
                    
                    #### NEXT ROW
                    col1, col2, col3, col4, col5 = st.columns(5)
                    st.subheader(f"Vereinsinformationen für {selected_team_name}")
                    col1.metric("aktuelle Form", evaluate_team_form(session, selected_team_name))
                    col2.metric("A-Nationalspieler", club_info.national_team_players)
                    col3.metric("Punkteschnitt", calculate_league_average_points(session, selected_team_name))
                    col4.metric("bevorzugte Aufstellung", get_preferred_formation_by_team_name(session, selected_team_name))
                    col5.metric("Liga", get_selected_team_id(session, selected_team_name))
                # Spalten für Spielerinformationen und Top Scorer Diagramm
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Spielerinformationen")
                    players = get_players_by_team(session, selected_team_name)
                    df_players = create_players_df(players)
                    # Scrollbare Tabelle für die Spielerinformationen
                    st.write(df_players, use_container_width=True)   
                with col2:
                    st.subheader("Top 10 Scorer")
                    top_scorers_df = get_top_scorers(session, selected_team_id)
                    if not top_scorers_df.empty:
                        plot_top_scorers_bar(top_scorers_df)
                    else:
                        st.write("Keine Daten über die Top Scorer verfügbar.")
                
                st.subheader("Spielperfomance über die Saison")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    plot_points_over_season(session, selected_team_name)
                with col2:
                    plot_home_away_game_results_bar(session, selected_team_name)
                with col3:
                    plot_game_outcomes(session, selected_team_name)
        with tab2:
            st.subheader('Teamvergleich (H2H)')
            team1_col, team2_col = st.columns([3, 3])
            teams = session.query(DimClub).all()

            with team1_col:
                team1_image_col, team1_name_col = st.columns([1, 3])
                team1_name = team1_name_col.selectbox("Wähle Team 1", [team.name for team in teams], key="team1")
                team1 = session.query(DimClub).filter(DimClub.name == team1_name).first()
                if team1:
                    club1_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{team1.club_id}.png?lm=1656580823"
                    team1_image_col.image(club1_logo_url, width=75)

            with team2_col:
                team2_name_col, team2_image_col = st.columns([3, 1])
                team2_name = team2_name_col.selectbox("Wähle Team 2", [team.name for team in teams], key="team2")
                team2 = session.query(DimClub).filter(DimClub.name == team2_name).first()
                if team2:
                    club2_logo_url = f"https://tmssl.akamaized.net/images/wappen/head/{team2.club_id}.png?lm=1656580823"
                    team2_image_col.image(club2_logo_url, width=75)

            if team1 and team2:
                team1_id = team1.club_id
                team2_id = team2.club_id
                
                team_names, categories, team_metrics = compare_team_performance(session, team1_id, team2_id)

                team1_name_col, metric_cols, team2_name_col = st.columns([2, 4, 2])
                team1_name_col.markdown(f"<h3 style='text-align: center;'>{team1.name}</h3>", unsafe_allow_html=True)
                team2_name_col.markdown(f"<h3 style='text-align: center;'>{team2.name}</h3>", unsafe_allow_html=True)

                for metric, team1_value, team2_value in zip(categories, team_metrics[0], team_metrics[1]):
                    team1_metric_col, metric_label_col, team2_metric_col = metric_cols.columns([2, 2, 2])

                    if team1_value is not None and team2_value is not None:
                        if team1_value > team2_value:
                            team1_metric_col.markdown(f"""
                            <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #155724; font-size: 20px; font-weight: bold; margin: 0;">{team1_value:.2f} <span style="color: green;">+{team1_value - team2_value:.2f}</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                            team2_metric_col.markdown(f"""
                            <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #721c24; font-size: 20px; font-weight: bold; margin: 0;">{team2_value:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        elif team2_value > team1_value:
                            team1_metric_col.markdown(f"""
                            <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #721c24; font-size: 20px; font-weight: bold; margin: 0;">{team1_value:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            team2_metric_col.markdown(f"""
                            <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #155724; font-size: 20px; font-weight: bold; margin: 0;">{team2_value:.2f} <span style="color: green;">+{team2_value - team1_value:.2f}</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            team1_metric_col.markdown(f"""
                            <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">{team1_value:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            team2_metric_col.markdown(f"""
                            <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                                <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">{team2_value:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        team1_metric_col.markdown(f"""
                        <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">-</p>
                        </div>
                        """, unsafe_allow_html=True)
                        team2_metric_col.markdown(f"""
                        <div style="background-color: #e9ecef; padding: 15px; border-radius: 10px; text-align: center;">
                            <p style="color: #495057; font-size: 20px; font-weight: bold; margin: 0;">-</p>
                        </div>
                        """, unsafe_allow_html=True)

                    metric_label_col.markdown(f"<p style='text-align: center; font-weight: bold; font-size: 15px;  margin-top: 19px;'>{metric}</p>", unsafe_allow_html=True)
            else:
                st.warning('Eines oder beide Teams nicht gefunden.')



if __name__ == '__main__':
   main()