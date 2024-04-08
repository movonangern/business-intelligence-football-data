#!/bin/bash

# Docker Compose ausführen
docker-compose up -d

# Warten, bis alle Docker-Compose-Dienste gestartet sind
until docker-compose ps | grep -q "Up"; do
  sleep 1
done

# Python-Skripte ausführen, um die Datenbank zu befüllen und zu bereinigen
python fill_database.py
python clean_data.py

# Streamlit-Anwendung starten
streamlit run Startseite.py