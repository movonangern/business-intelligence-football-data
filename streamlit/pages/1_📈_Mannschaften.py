import streamlit as st
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
from utils.ORM_model import DimPlayer, DimClub

# Datenbankverbindung einrichten
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def calculate_age(birth_date_str):
    if not birth_date_str:
        return "Unbekannt"
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except ValueError:
        return "Unbekannt"

def get_club_info(selected_team_name):
    club_info = session.query(DimClub).filter(DimClub.name == selected_team_name).first()
    return club_info

def get_players_by_team(selected_team_name):
    return session.query(DimPlayer).join(DimClub, DimPlayer.current_club_id == DimClub.club_id)\
        .filter(DimClub.name == selected_team_name).all()

def create_players_df(players):
    players_data = [{
        "Bild": f'<img src="{player.image_url}" width="50" height="50">' if player.image_url else 'Kein Bild',
        "Name": player.name,
        "Alter": calculate_age(player.date_of_birth),
        "Position": player.position,
        "Nationalität": player.country_of_birth,
        "Marktwert (€)": "{:,}".format(player.market_value_in_eur).replace(',', '.') if player.market_value_in_eur else 'Unbekannt',
        "Vertragszeit": datetime.strptime(player.contract_expiration_date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y") if player.contract_expiration_date else 'Unbekannt'
    } for player in players if player.contract_expiration_date is not None]
    return pd.DataFrame(players_data)

def main():
    st.set_page_config(layout='wide')
    st.title("Mannschaftsauswertung")
    
    # Auswahl der Mannschaft
    teams = session.query(DimClub.name).distinct().all()
    team_names = [team[0] for team in teams]
    selected_team_name = st.selectbox("Wähle eine Mannschaft", team_names)

    if selected_team_name:
        club_info = get_club_info(selected_team_name)
        if club_info:
            st.subheader(f"Vereinsinformationen für {selected_team_name}")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Kadergröße", str(club_info.squad_size))
            net_transfer_value = club_info.net_transfer_record.strip().replace('€', '').replace('m', ' Mio').replace('k', ' K').replace('+', '').replace('-', '')
            if '-' in club_info.net_transfer_record:
                col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Verlust", delta_color="inverse")
            else:
                col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Gewinn", delta_color="normal")
            col3.metric("Anteil Legionäre (%)", f"{float(club_info.foreigners_percentage)} %")
            col4.metric("Durchschnittsalter", float(club_info.average_age))
            col5.metric("Teamwert (€)", f"{club_info.total_market_value:,} €" if club_info.total_market_value else "0 €")
            col6.metric("A-Nationalspieler", club_info.national_team_players)

        # Spielerinformationen anzeigen
        st.subheader("Spielerinformationen")
        players = get_players_by_team(selected_team_name)
        df_players = create_players_df(players)
        
        # CSS-Stil und Tabelle in einen scrollbaren Container einbetten
        st.markdown("""
            <style>
            .scrollable-container {
                height: 400px;  /* oder die gewünschte Höhe */
                overflow-y: auto;
            }
            .scrollable-container::-webkit-scrollbar {
                width: 5px;
            }
            .scrollable-container::-webkit-scrollbar-thumb {
                background: #888;
            }
            .scrollable-container::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            .stTable {
                color: black;
            }
            img {
                border-radius: 50%;
                margin-right: 10px;
            }
            </style>
            """, unsafe_allow_html=True)
        
        # Konvertierung des DataFrame zu HTML und Einsatz von st.markdown zum Anzeigen
        st.markdown(f"""
            <div class="scrollable-container">
            {df_players.to_html(escape=False, index=False)}
            </div>
            """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
