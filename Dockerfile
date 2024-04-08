FROM python:latest

# Grundlegende Umgebungsvariablen festlegen
ENV MYSQL_ROOT_PASSWORD=root \
    MYSQL_DATABASE=football_db \
    PMA_HOST=db \
    PMA_USER=root \
    PMA_PASSWORD=root

# Kopieren des Projektverzeichnisses in das Image
COPY . /app
WORKDIR /app

# Installieren der Python-Abhängigkeiten
RUN pip install -r requirements.txt

# Exponieren der Ports für MySQL, phpMyAdmin und Streamlit
EXPOSE 8501

# Python-Skripte ausführen, um die Datenbank zu befüllen und zu bereinigen
# RUN python fill_database.py
# RUN python clean_data.py

# Streamlit-Anwendung starten
CMD ["python", "entrypoint.py"] && ["streamlit", "run", "Startseite.py"]