from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from ORM_model import DimPlayer

# Datenbank-Verbindung herstellen
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Abfrage zur Tabelle DimPlayer erstellen
query = session.query(DimPlayer)

# Abfrage ausführen und Ergebnisse in einen Pandas-DataFrame laden
df_players = pd.read_sql(query.statement, query.session.bind)

# DataFrame in eine CSV-Datei schreiben
df_players.to_csv('df_players_with_metrics.csv', index=False)

print("Die Daten wurden erfolgreich in die Datei 'df_players.csv' geschrieben.")