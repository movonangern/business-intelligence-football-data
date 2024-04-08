from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import streamlit as st
from lib.Markt.lib_markt import get_basic_filtered_players
from ENV import DATABASE_URL

# Datenbankverbindung einrichten
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def main():
    st.set_page_config(layout='wide')
    st.title("Spieleridentifikation")

    with Session() as session:
        col_alter_min,  col_foot, col_position = st.columns(3)
        with col_alter_min:
            age_range = st.slider("Alter", 15, 50, (25, 35))
            min_age, max_age = age_range
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

        col_1, col_2, col_3, col_4 = st.columns(4)
        with col_1:
            min_defensive_contribution = st.slider('Minimale defensive Beitrag', 0.0, 1.0, 0.0, 0.01)
        with col_2:
            min_passing_efficiency = st.slider('Minimale Passgenauigkeit', 0.0, 1.0, 0.0, 0.01)
        with col_3:
            min_goal_contribution = st.slider('Minimale Torbeteiligung', 0.0, 1.0, 0.0, 0.01)
        with col_4:
            min_dribbling_ability = st.slider('Minimale Dribbling-Fähigkeit', 0.0, 1.0, 0.0, 0.01)

        col_5, col_6, col_7, col_8 = st.columns(4)
        with col_5:
            min_shot_efficiency = st.slider('Minimale Schusseffizienz', 0.0, 1.0, 0.0, 0.01)
        with col_6:
            min_discipline = st.slider('Minimale Disziplin', 0.0, 1.0, 0.0, 0.01)
        with col_7:
            min_involvement = st.slider('Minimale Beteiligung', 0.0, 1.0, 0.0, 0.01)
        with col_8:
            min_overall_rating = st.slider('Minimale Gesamtbewertung', 0.0, 1.0, 0.0, 0.01)

                    
        basic_filtered_players_df = get_basic_filtered_players(session, min_age, max_age, feet, position, min_value, max_value, contract_expiration_str,
                               min_defensive_contribution, min_passing_efficiency,
                               min_goal_contribution, min_dribbling_ability,
                               min_shot_efficiency, min_discipline,
                               min_involvement, min_overall_rating)
        
        st.dataframe(basic_filtered_players_df, use_container_width=True)
        
if __name__ == "__main__":
    main()