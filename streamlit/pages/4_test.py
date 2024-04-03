import streamlit as st
from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import sessionmaker
from utils.ORM_model import DimPlayer

# Streamlit-App-Konfiguration
st.set_page_config(page_title='Spielerpositionen', layout='wide')

DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)  
Session = sessionmaker(bind=engine)
session = Session()

# Streamlit-App-Inhalt
st.title('Mögliche Positionen der Spieler')

# Alle eindeutigen Positionen abrufen
positions = session.query(distinct(DimPlayer.position)).all()

# Positionen als Liste extrahieren
position_list = [position[0] for position in positions]

# Positionen anzeigen
st.write('Hier sind die möglichen Positionen der Spieler:')
for position in position_list:
    st.write(f'- {position}')

# Verbindung zur Datenbank schließen
session.close()