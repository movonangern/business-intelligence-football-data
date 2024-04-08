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
EXPOSE 3306 8080 8501

# Installation von Docker Compose
RUN apt-get update && \
    apt-get install -y docker.io docker-compose

# Bash-Skript zum Warten auf Docker-Compose-Dienste und Starten der Anwendung kopieren
COPY entrypoint.sh /app/entrypoint.sh

# Rechte für das Bash-Skript setzen
RUN chmod +x /app/entrypoint.sh

# Bash-Skript als Startbefehl festlegen
CMD ["bash", "entrypoint.sh"]