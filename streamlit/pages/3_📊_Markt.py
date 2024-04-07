from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, or_, extract, cast, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import Date
import pandas as pd
import streamlit as st
from utils.ORM_model import DimPlayer
from lib.Spieler.lib_spieler import get_player_stats

# Datenbankverbindung einrichten
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def calculate_age(birth_date_str):
    if not birth_date_str:
        return "Unbekannt"
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def get_basic_filtered_players(session, min_age, max_age, feet, position, min_value, max_value, contract_expiration_str):
    query = session.query(DimPlayer)

    if min_age is not None:
        max_birth_date = datetime(datetime.today().year - min_age, datetime.today().month, datetime.today().day).date()
        query = query.filter(DimPlayer.date_of_birth <= max_birth_date)

    if max_age is not None:
        min_birth_date = datetime(datetime.today().year - max_age, datetime.today().month, datetime.today().day).date()
        query = query.filter(DimPlayer.date_of_birth >= min_birth_date)

    if feet:
        query = query.filter(DimPlayer.foot.in_(feet))

    if position:
        query = query.filter(DimPlayer.position == position)

    if min_value is not None:
        query = query.filter(DimPlayer.market_value_in_eur >= min_value)
    
    if max_value is not None:
        query = query.filter(DimPlayer.market_value_in_eur <= max_value)

    if contract_expiration_str:
        expiration_date = datetime.strptime(contract_expiration_str, "%Y-%m-%d %H:%M:%S").date()
        query = query.filter(or_(
            DimPlayer.contract_expiration_date >= expiration_date, 
            DimPlayer.contract_expiration_date.is_(None)
        ))

    return pd.DataFrame([{
        'Name': player.name,
        'Alter': calculate_age(player.date_of_birth) if player.date_of_birth else 'Unbekannt',
        'Verein': player.current_club_name,
        'Position': player.position,
        'Fuß': player.foot,
        'Größe': player.height_in_cm,
        'Marktwert': player.market_value_in_eur,
        'Vertragsauslaufzeit': datetime.strptime(player.contract_expiration_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d') if isinstance(player.contract_expiration_date, str) else player.contract_expiration_date.strftime('%Y-%m-%d') if player.contract_expiration_date is not None else 'Unbekannt',
        'Agent': player.agent_name,
    } for player in query.all()])


def main():
    st.set_page_config(layout='wide')
    st.title("Spieleridentifikation")

    with Session() as session:
        col_alter_min, col_alter_max, col_foot, col_position = st.columns(4)
        with col_alter_min:
            min_age = st.slider('Mindestalter', 15, 40, 18) 
        with col_alter_max:
            max_age = st.slider('Höchstalter', 15, 40, 35)
        with col_foot:
            feet = st.multiselect('Fuß', ['left', 'right'], default=['left', 'right'])
        with col_position:
            positions = ['Goalkeeper', 'Defender', 'Midfield', 'Attack']
            position = st.selectbox('Position', [''] + positions, index=0)

        col_value_min, col_value_max, col_contract = st.columns(3)
        with col_value_min:
            min_value = st.slider('Mindestmarktwert (€)', 0, 100000000, 0, 500000)
        with col_value_max:
            max_value = st.slider('Höchstmarktwert (€)', 0, 100000000, 50000000, 500000)
        with col_contract:
            contract_options = ["Alle", "Nächsten 6 Monate", "Nächstes Jahr", "Nächsten 2 Jahre"]
            contract_expiration_selection = st.selectbox("Vertragsauslaufzeit", contract_options)
            if contract_expiration_selection != "Alle":
                if contract_expiration_selection == "Nächsten 6 Monate":
                    contract_expiration_str = (datetime.today() + timedelta(days=183)).strftime("%Y-%m-%d %H:%M:%S")
                elif contract_expiration_selection == "Nächstes Jahr":
                    contract_expiration_str = (datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                elif contract_expiration_selection == "Nächsten 2 Jahre":
                    contract_expiration_str = (datetime.today() + timedelta(days=730)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                contract_expiration_str = None

 
        basic_filtered_players_df = get_basic_filtered_players(session, min_age, max_age, feet, position, min_value, max_value, contract_expiration_str)
        st.dataframe(basic_filtered_players_df, use_container_width=True)

        col_1, col_2, col_3, col_4 = st.columns(4)
        with col_1:
            min_value = col_1.slider('Mindestmarktwert (€)', 0, 100000000, 0, 500000, key="1")
        with col_2:
            # Sie können einer Variablen den gleichen Namen geben oder sie auch weglassen, wenn Sie den Wert nicht speichern möchten
            col_2.slider('Mindestmarktwert (€)', 0, 100000000, 0, 500000, key="2")
        with col_3:
            col_3.slider('Mindestmarktwert (€)', 0, 100000000, 0, 500000, key="3")
        with col_4:
            col_4.slider('Mindestmarktwert (€)', 0, 100000000, 0, 500000, key="4") 
            
if __name__ == "__main__":
    main()