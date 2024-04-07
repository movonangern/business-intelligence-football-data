from sqlalchemy import create_engine, update, func, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from math import ceil
from ORM_model import Base, DimPlayer, FactAppearance
import time
from sqlalchemy.dialects.mysql import insert

# Datenbank-Verbindung herstellen
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Setze die Isolationsstufe auf READ UNCOMMITTED
session.execute(text("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))

def player_age(date_of_birth):
    today = pd.to_datetime('today')
    return today.year - pd.to_datetime(date_of_birth).year

def normalize_metric(value, min_value=None, max_value=None):
    if min_value is None:
        min_value = 0
    if max_value is None:
        max_value = 1

    if value is None:
        return None

    value = max(min(value, max_value), min_value)
    return (value - min_value) / (max_value - min_value)

def calculate_weighted_stat(appearances, stat_name, weight_factor):
    total_minutes_played = sum(a.minutes_played or 0 for a in appearances if a.minutes_played is not None)
    weighted_sum = sum(((getattr(a, stat_name, 0) or 0) * (a.minutes_played or 0) / 90) for a in appearances if a.minutes_played is not None and getattr(a, stat_name, None) is not None)
    return weighted_sum / (total_minutes_played / 90) * weight_factor if total_minutes_played else 0

def get_player_stats(player_id):
    appearances = session.query(FactAppearance).filter(FactAppearance.player_id == player_id).all()
    total_minutes_played = session.query(func.sum(FactAppearance.minutes_played)).filter(FactAppearance.player_id == player_id, FactAppearance.goals2 != None).scalar()
    total_stats = session.query(func.sum(FactAppearance.goals2), func.sum(FactAppearance.assists), func.sum(FactAppearance.yellow_card), func.sum(FactAppearance.red_card)).filter(FactAppearance.player_id == player_id).first()

    # Gewichtete Statistiken berechnen
    goal_contribution = normalize_metric(calculate_weighted_stat(appearances, 'goals2', 1.0) + calculate_weighted_stat(appearances, 'assists', 0.5))
    defensive_contribution = normalize_metric(calculate_weighted_stat(appearances, 'number_of_tackles', 0.5) + calculate_weighted_stat(appearances, 'blocks', 0.5))
    passing_efficiency = normalize_metric(calculate_weighted_stat(appearances, 'successful_passes', 1.0) / (calculate_weighted_stat(appearances, 'attempted_passes', 1.0) or 1))
    dribbling_ability = normalize_metric(calculate_weighted_stat(appearances, 'successful_dribbling', 1.0) / (calculate_weighted_stat(appearances, 'attempted_dribbles', 1.0) or 1))
    shot_efficiency = normalize_metric(calculate_weighted_stat(appearances, 'shots_on_target', 1.0) / (calculate_weighted_stat(appearances, 'shots', 1.0) or 1))
    discipline = normalize_metric(1 - (calculate_weighted_stat(appearances, 'yellow_card', 5.0) + calculate_weighted_stat(appearances, 'red_card', 10.0)))
    involvement = normalize_metric(calculate_weighted_stat(appearances, 'touches', 1) + calculate_weighted_stat(appearances, 'carries', 1), 0, 200)

    # Berechnung des Overall Ratings
    overall_rating = (goal_contribution + defensive_contribution + passing_efficiency + dribbling_ability + shot_efficiency + discipline + involvement) / 7

    return {
        'total_minutes_played': total_minutes_played,
        'total_stats': total_stats,
        'goal_contribution': goal_contribution,
        'defensive_contribution': defensive_contribution,
        'passing_efficiency': passing_efficiency,
        'dribbling_ability': dribbling_ability,
        'shot_efficiency': shot_efficiency,
        'discipline': discipline,
        'involvement': involvement,
        'overall_rating': overall_rating
    }

def update_player_metrics():
    start_time = time.time()  # Startzeit speichern

    all_player_stats = {}
    player_ids_with_appearances = session.query(FactAppearance.player_id).distinct().all()
    players = session.query(DimPlayer).filter(DimPlayer.player_id.in_([id[0] for id in player_ids_with_appearances])).all()
    total_players = len(players)

    print(f"Berechne Metriken für {total_players} Spieler...")

    # Berechne Metriken für alle Spieler
    for player in players:
        player_stats = get_player_stats(player.player_id)
        all_player_stats[player.player_id] = player_stats

    # Aktualisiere die Tabelle DimPlayer mit den berechneten Metriken in Chunks
    chunk_size = 500  # Größe der Chunks
    total_chunks = ceil(total_players / chunk_size)
    print(f"Es werden {total_chunks} Chunks benötigt, um die Metriken für {total_players} Spieler zu aktualisieren.")

    chunk_count = 0
    for i in range(0, total_players, chunk_size):
        chunk_count += 1
        print(f"Chunk {chunk_count}/{total_chunks} wird verarbeitet. Verstrichene Zeit: {time.time() - start_time:.2f} Sekunden.")

        chunk_player_ids = [player.player_id for player in players[i:i+chunk_size]]
        update_statements = [
            insert(DimPlayer)
            .values(
                player_id=player_id,
                goal_contribution=all_player_stats[player_id]['goal_contribution'],
                defensive_contribution=all_player_stats[player_id]['defensive_contribution'],
                passing_efficiency=all_player_stats[player_id]['passing_efficiency'],
                dribbling_ability=all_player_stats[player_id]['dribbling_ability'],
                shot_efficiency=all_player_stats[player_id]['shot_efficiency'],
                discipline=all_player_stats[player_id]['discipline'],
                involvement=all_player_stats[player_id]['involvement'],
                overall_rating=all_player_stats[player_id]['overall_rating']
            )
            .on_duplicate_key_update(
                goal_contribution=all_player_stats[player_id]['goal_contribution'],
                defensive_contribution=all_player_stats[player_id]['defensive_contribution'],
                passing_efficiency=all_player_stats[player_id]['passing_efficiency'],
                dribbling_ability=all_player_stats[player_id]['dribbling_ability'],
                shot_efficiency=all_player_stats[player_id]['shot_efficiency'],
                discipline=all_player_stats[player_id]['discipline'],
                involvement=all_player_stats[player_id]['involvement'],
                overall_rating=all_player_stats[player_id]['overall_rating']
            )
            for player_id in chunk_player_ids
        ]

        for stmt in update_statements:
            session.execute(stmt)
        session.commit()

    print(f"Aktualisierung der Spielermetriken abgeschlossen. Gesamtzeit: {time.time() - start_time:.2f} Sekunden.")

if __name__ == '__main__':
    # Erstelle die Tabellen in der Datenbank, falls sie noch nicht existieren
    Base.metadata.create_all(engine)

    # Führe die Aktualisierung der Spielermetriken aus
    update_player_metrics()