#streamlit/lib/Mannschaften/lib_mannschaften.py

import streamlit as st
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
from utils.ORM_model import DimPlayer, DimClub, FactAppearance, DimGame
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import numpy as np

# Datenbankverbindung einrichten
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def calculate_age(birth_date_str):
    if not birth_date_str:
        return "Unbekannt"
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except ValueError:
        return "Unbekannt"

def get_club_info(session, selected_team_name):
    club_info = session.query(DimClub).filter(DimClub.name == selected_team_name).first()
    return club_info

def get_selected_team_id(session, selected_team_name):
    return session.query(DimClub).filter(DimClub.name == selected_team_name).first().domestic_competition_id

def get_players_by_team(session, selected_team_name):
    return session.query(DimPlayer).join(DimClub, DimPlayer.current_club_id == DimClub.club_id)\
        .filter(DimClub.name == selected_team_name).all()

def create_players_df(players):
    players_data = [{
        "Name": player.name,
        "Alter": calculate_age(player.date_of_birth),
        "Position": player.position,
        "Nationalität": player.country_of_birth,
        "Marktwert (€)": "{:,}".format(player.market_value_in_eur).replace(',', '.') if player.market_value_in_eur else 'Unbekannt',
        "Vertragszeit": datetime.strptime(player.contract_expiration_date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y") if player.contract_expiration_date else 'Unbekannt'
    } for player in players if player.contract_expiration_date is not None]
    return pd.DataFrame(players_data)

def get_current_season_start():
    """Gibt das Startdatum der aktuellen Saison zurück."""
    today = datetime.today()
    return datetime(today.year if today.month >= 8 else today.year - 1, 8, 1)

def get_club_total_market_value(session, club_id):
    """Berechnet den Gesamtwert des Teams basierend auf den Marktwerten der Spieler."""
    players = session.query(DimPlayer).filter(DimPlayer.current_club_id == club_id).all()
    total_market_value = sum(player.market_value_in_eur if player.market_value_in_eur else 0 for player in players)
    return total_market_value



def get_top_scorers(session, club_id, top_n=10):
    """Query the top scorers for the specified club for the current season."""
    season_start = get_current_season_start()
    
    top_scorers = (session.query(
                        FactAppearance.player_name, 
                        func.sum(FactAppearance.goals1).label('goals'),
                        func.sum(FactAppearance.assists).label('assists'))
                    .join(DimPlayer, DimPlayer.player_id == FactAppearance.player_id)
                    .filter(DimPlayer.current_club_id == club_id,
                            func.date(FactAppearance.date) >= season_start)
                    .group_by(FactAppearance.player_name)
                    .order_by(func.sum(FactAppearance.goals1 + FactAppearance.assists).desc())
                    .limit(top_n)
                    .all())
    
    return pd.DataFrame(top_scorers, columns=['Player', 'Goals', 'Assists'])

def plot_top_scorers_bar(df):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df['Player'],
        x=df['Goals'],
        orientation='h',
        name='Tore',
        marker=dict(
            color='blue'
        )
    ))
    fig.add_trace(go.Bar(
        y=df['Player'],
        x=df['Assists'],
        orientation='h',
        name='Assists',
        marker=dict(
            color='red'
        )
    ))
    
    fig.update_layout(
        title="Summierte Assists und Spieler",
        barmode='stack',
        xaxis=dict(title='Anzahl'),
        yaxis=dict(title='Spieler')
    )
    
    st.plotly_chart(fig)

def get_last_five_games(session, selected_team_name):
    """Gets the last five games of the selected team."""
    season_start = get_current_season_start()
    games = (session.query(DimGame)
             .filter(
                 ((DimGame.home_club_name == selected_team_name) |
                  (DimGame.away_club_name == selected_team_name)) &
                 (func.date(DimGame.date) >= season_start))
             .order_by(DimGame.date.desc())
             .limit(5)
             .all())
    return games

def calculate_current_form(session, selected_team_name):
    """Calculates the current form based on the last five games."""
    last_five_games = get_last_five_games(session, selected_team_name)
    points = 0
    if last_five_games:
        for game in last_five_games:
            if game.home_club_name == selected_team_name:
                if game.home_club_goals > game.away_club_goals:
                    points += 3
                elif game.home_club_goals == game.away_club_goals:
                    points += 1
            else:
                if game.away_club_goals > game.home_club_goals:
                    points += 3
                elif game.away_club_goals == game.home_club_goals:
                    points += 1
        return points / len(last_five_games)
    else:
        return 0  # Rückgabe eines Standardwerts, wenn keine Spiele vorhanden sind

def plot_home_away_game_results_bar(session, selected_team_name):
    season_start = get_current_season_start()

    # Spiele des ausgewählten Teams abrufen
    games = session.query(DimGame).filter(
        ((DimGame.home_club_name == selected_team_name) | (DimGame.away_club_name == selected_team_name)) &
        (func.date(DimGame.date) >= season_start)
    ).all()

    # Heim- und Auswärtsergebnisse zählen
    home_results = {'Gewonnen': 0, 'Unentschieden': 0, 'Verloren': 0}
    away_results = {'Gewonnen': 0, 'Unentschieden': 0, 'Verloren': 0}

    for game in games:
        if game.home_club_name == selected_team_name:  # Heimspiel
            if game.home_club_goals > game.away_club_goals:
                home_results['Gewonnen'] += 1
            elif game.home_club_goals == game.away_club_goals:
                home_results['Unentschieden'] += 1
            else:
                home_results['Verloren'] += 1
        else:  # Auswärtsspiel
            if game.away_club_goals > game.home_club_goals:
                away_results['Gewonnen'] += 1
            elif game.away_club_goals == game.home_club_goals:
                away_results['Unentschieden'] += 1
            else:
                away_results['Verloren'] += 1

    # Farben für die Balken festlegen
    colors = ['green', 'orange', 'red']  # Beispielhafte Farben für Gewonnen, Unentschieden, Verloren

    # Ergebnisse in ein Bar-Chart visualisieren
    fig = go.Figure(data=[
        go.Bar(name='Gewonnen', x=['Heim', 'Auswärts'], y=[home_results['Gewonnen'], away_results['Gewonnen']], marker_color=colors[0]),
        go.Bar(name='Unentschieden', x=['Heim', 'Auswärts'], y=[home_results['Unentschieden'], away_results['Unentschieden']], marker_color=colors[1]),
        go.Bar(name='Verloren', x=['Heim', 'Auswärts'], y=[home_results['Verloren'], away_results['Verloren']], marker_color=colors[2])
    ])

    # Layout anpassen
    fig.update_layout(
        barmode='group',
        title='Heim- vs. Auswärtsspiel-Performance',
        xaxis=dict(title='Spielort', tickmode='array', tickvals=['Heim', 'Auswärts']),
        yaxis=dict(title='Anzahl der Spiele'),
        legend_title='Spielresultate',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Chart in Streamlit darstellen
    st.plotly_chart(fig)

def calculate_league_form_quantiles(session):
    """Calculates the 25th and 75th percentile of league's form."""
    all_teams_form = [calculate_current_form(session, team.name) for team in session.query(DimClub).all()]
    return np.percentile(all_teams_form, [25, 75])

def evaluate_team_form(session, selected_team_name):
    """Evaluates the form of the selected team relative to the league."""
    team_form = calculate_current_form(session, selected_team_name)
    quantiles = calculate_league_form_quantiles(session)
    if team_form >= quantiles[1]:
        return "Sehr gut"
    elif team_form >= quantiles[0]:
        return "Normal"
    else:
        return "Schlecht"

def calculate_league_average_points(session, selected_team_name):
    """Calculates the average points per game for the selected team since August 1st."""
    season_start = get_current_season_start()
    
    # Datenstrukturen zur Verfolgung der Gesamtpunktzahl und der Anzahl der Spiele für das ausgewählte Team erstellen
    total_points = 0
    total_games = 0
    
    # Spiele des ausgewählten Teams seit dem Saisonstart abrufen
    games = session.query(DimGame).filter(
        ((DimGame.home_club_name == selected_team_name) | (DimGame.away_club_name == selected_team_name)) &
        (func.date(DimGame.date) >= season_start)
    ).all()
    
    # Punkte für jedes Spiel addieren
    for game in games:
        total_games += 1
        if game.home_club_name == selected_team_name:
            if game.home_club_goals > game.away_club_goals:
                total_points += 3
            elif game.home_club_goals == game.away_club_goals:
                total_points += 1
        else:
            if game.away_club_goals > game.home_club_goals:
                total_points += 3
            elif game.away_club_goals == game.home_club_goals:
                total_points += 1
                
    # Durchschnittliche Punkte berechnen und auf zwei Nachkommastellen runden
    if total_games > 0:
        average_points = round(total_points / total_games, 2)
    else:
        average_points = 0
            
    return average_points


def get_team_preferred_formation(session, selected_team_name):
    """Gets the preferred formation of the selected team."""
    # Here you can implement logic to determine the preferred formation based on historical data or coach preferences
    return "4-3-3"  # Placeholder value




def get_preferred_formation_by_team_name(session, selected_team_name):
    # Saisonstart bestimmen, um nur Spiele der aktuellen Saison zu berücksichtigen
    season_start = get_current_season_start()

    # Aufstellungen des Vereins in Heim- und Auswärtsspielen abfragen
    formations = session.query(DimGame.home_club_formation)\
                        .filter(DimGame.home_club_name == selected_team_name,
                                DimGame.date >= season_start)\
                        .union(session.query(DimGame.away_club_formation)\
                        .filter(DimGame.away_club_name == selected_team_name,
                                DimGame.date >= season_start))\
                        .all()

    # Ein Dictionary zur Speicherung der Häufigkeit jeder Formation erstellen
    formation_count = {}

    # Die Häufigkeit jeder Formation zählen
    for formation in formations:
        # Da 'formation' ein Tupel ist, greifen wir mit [0] auf das Element zu
        formation_str = formation[0]  
        if formation_str in formation_count:
            formation_count[formation_str] += 1
        else:
            formation_count[formation_str] = 1

    # Die am häufigsten verwendete Formation bestimmen
    if formation_count:  # Sicherstellen, dass das Dictionary nicht leer ist
        preferred_formation = max(formation_count, key=formation_count.get)
    else:
        preferred_formation = "Keine Daten"

    return preferred_formation

def plot_points_over_season(sess, selected_team_name):
    """Plots the points over the season for the selected team with Plotly."""
    # Das Startdatum der aktuellen Saison abrufen
    season_start = get_current_season_start()

    # Spiele der aktuellen Saison abrufen
    games = sess.query(
        DimGame.date,
        DimGame.home_club_name, 
        DimGame.away_club_name,
        DimGame.home_club_goals, 
        DimGame.away_club_goals
    ).filter(
        ((DimGame.home_club_name == selected_team_name) | 
         (DimGame.away_club_name == selected_team_name)) &
        (func.date(DimGame.date) >= season_start)
    ).order_by(DimGame.date).all()

    # Berechnung der Punkte für jedes Spiel
    dates = []
    points_per_game = []
    total_points = 0
    for game in games:
        dates.append(game.date)
        if game.home_club_name == selected_team_name:
            if game.home_club_goals > game.away_club_goals:
                total_points += 3
            elif game.home_club_goals == game.away_club_goals:
                total_points += 1
        elif game.away_club_goals > game.home_club_goals:
                total_points += 3
        elif game.away_club_goals == game.home_club_goals:
                total_points += 1
        points_per_game.append(total_points)

    # Plotly Figur erstellen
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=points_per_game, mode='lines+markers', name='Punkte'))
    
    # Layout der Figur aktualisieren
    fig.update_layout(
        title=f'Punkteverlauf über die Saison für {selected_team_name}',
        xaxis_title='Datum',
        yaxis_title='Gesamtpunkte',
        yaxis=dict(range=[0, max(points_per_game)+3])  # Range etwas erhöhen für bessere Visualisierung
    )

    # Diagramm anzeigen
    st.plotly_chart(fig)
    
def create_radar_chart(team_names, categories, values):
    data = []
    for team_name, value in zip(team_names, values):
        data.append(go.Scatterpolar(
            r=value,
            theta=categories,
            fill='toself',
            name=team_name
        ))

    layout = go.Layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(values)]
            )
        ),
        showlegend=True
    )

    fig = go.Figure(data=data, layout=layout)
    return fig

def plot_team_performance_over_season(session, selected_team_name):
    season_start = get_current_season_start()

    # Daten für die Spiele des Teams abrufen
    games = (session.query(
                DimGame.date, 
                func.sum(FactAppearance.goals1).label('total_goals'),
                func.sum(FactAppearance.shots).label('total_shots'),
                func.sum(FactAppearance.shots_on_target).label('shots_on_target'))
             .join(FactAppearance, FactAppearance.game_id == DimGame.game_id)
             .join(DimClub, DimClub.club_id == FactAppearance.player_club_id)
             .filter(DimClub.name == selected_team_name, 
                     func.date(DimGame.date) >= season_start)
             .group_by(DimGame.date)
             .order_by(DimGame.date)
             .all())

    # Daten in ein DataFrame umwandeln
    df = pd.DataFrame(games, columns=['Date', 'Total Goals', 'Total Shots', 'Shots on Target'])
    
    # Liniendiagramm mit Plotly erstellen
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Total Goals'], mode='lines+markers', name='Tore'))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Total Shots'], mode='lines+markers', name='Schüsse'))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Shots on Target'], mode='lines+markers', name='Schüsse aufs Tor'))

    fig.update_layout(xaxis_title='Datum',
                      yaxis_title='Anzahl',
                      legend_title='Metriken')
    
    st.plotly_chart(fig)

def calculate_shooting_accuracy(session, selected_team_name):
    # Mannschafts-ID abrufen
    selected_team_id = session.query(DimClub).filter(DimClub.name == selected_team_name).first().club_id
    
    # Tore und Torschüsse für die ausgewählte Mannschaft abrufen
    goals_query = session.query(func.sum(DimGame.home_club_goals).label('home_goals'), func.sum(DimGame.away_club_goals).label('away_goals')).\
                  filter((DimGame.home_club_id == selected_team_id) | (DimGame.away_club_id == selected_team_id))
    
    shots_query = session.query(func.sum(FactAppearance.shots).label('shots')).\
                  join(DimGame, DimGame.game_id == FactAppearance.game_id).\
                  filter((FactAppearance.player_club_id == selected_team_id) | (FactAppearance.player_current_club_id == selected_team_id))
    
    # Ergebnisse der Abfragen abrufen
    goals_result = goals_query.first()
    shots_result = shots_query.first()
    
    # Tore und Torschüsse extrahieren
    home_goals = goals_result.home_goals or 0
    away_goals = goals_result.away_goals or 0
    total_goals = home_goals + away_goals
    total_shots = shots_result.shots or 0
    
    # Torschussquote berechnen (in Prozent)
    if total_shots > 0:
        shooting_accuracy = (total_goals / total_shots) * 100
    else:
        shooting_accuracy = 0
    
    return shooting_accuracy

def plot_goal_effectiveness(session, selected_team_name):
    season_start = get_current_season_start()
    
    # Spiele des Teams abrufen
    games = (session.query(
                DimGame.date,
                DimGame.home_club_name, 
                DimGame.away_club_name, 
                DimGame.home_club_goals, 
                DimGame.away_club_goals)
             .filter(
                 ((DimGame.home_club_name == selected_team_name) | 
                  (DimGame.away_club_name == selected_team_name)) &
                 (func.date(DimGame.date) >= season_start))
             .all())
    
    # Daten für Heim- und Auswärtsspiele vorbereiten
    home_games = [{'goals': game.home_club_goals, 'result': game.home_club_goals - game.away_club_goals} for game in games if game.home_club_name == selected_team_name]
    away_games = [{'goals': game.away_club_goals, 'result': game.away_club_goals - game.home_club_goals} for game in games if game.away_club_name == selected_team_name]
    
    # Ergebnisse in DataFrame umwandeln
    home_df = pd.DataFrame(home_games)
    away_df = pd.DataFrame(away_games)
    
    # Ergebnis in Gewonnen, Verloren, Unentschieden umwandeln
    home_df['match_result'] = home_df['result'].apply(lambda x: 'Gewonnen' if x > 0 else ('Unentschieden' if x == 0 else 'Verloren'))
    away_df['match_result'] = away_df['result'].apply(lambda x: 'Gewonnen' if x > 0 else ('Unentschieden' if x == 0 else 'Verloren'))
    
    # Scatterplot erstellen
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=home_df['goals'], y=home_df['match_result'], mode='markers', name='Heim'))
    fig.add_trace(go.Scatter(x=away_df['goals'], y=away_df['match_result'], mode='markers', name='Auswärts'))
    
    # Layout aktualisieren
    fig.update_layout(
        title='Tore und Spielresultate (Heim vs. Auswärts)',
        xaxis_title='Anzahl der Tore',
        yaxis_title='Spielresultat',
        yaxis={'categoryorder':'array', 'categoryarray':['Verloren','Unentschieden','Gewonnen']}
    )

    # Diagramm anzeigen
    st.plotly_chart(fig)


    
def plot_game_outcomes(session, selected_team_name):
    season_start = get_current_season_start()

    # Spiele des Teams abrufen
    games = (session.query(
                DimGame.home_club_name, DimGame.away_club_name,
                DimGame.home_club_goals, DimGame.away_club_goals)
             .filter(
                 ((DimGame.home_club_name == selected_team_name) |
                  (DimGame.away_club_name == selected_team_name)) &
                 (func.date(DimGame.date) >= season_start))
             .all())

    # Spielresultate zählen
    results = {'Gewonnen': 0, 'Verloren': 0, 'Unentschieden': 0}
    for game in games:
        if game.home_club_name == selected_team_name:
            if game.home_club_goals > game.away_club_goals:
                results['Gewonnen'] += 1
            elif game.home_club_goals < game.away_club_goals:
                results['Verloren'] += 1
            else:
                results['Unentschieden'] += 1
        else:
            if game.away_club_goals > game.home_club_goals:
                results['Gewonnen'] += 1
            elif game.away_club_goals < game.home_club_goals:
                results['Verloren'] += 1
            else:
                results['Unentschieden'] += 1

    # Kreisdiagramm erstellen
    fig = go.Figure(data=[go.Pie(labels=list(results.keys()), values=list(results.values()))])
    fig.update_traces(hole=.4, hoverinfo="label+percent+name")
    fig.update_layout(title="Anteil der Spielresultate pro Saison")

    st.plotly_chart(fig)

def compare_team_performance(session, selected_team1_id, selected_team2_id):
    team_ids = [selected_team1_id, selected_team2_id]
    team_names = []
    team_metrics = []
    
    for team_id in team_ids:
        appearances = (session.query(FactAppearance)
                       .filter(FactAppearance.player_club_id == team_id)
                       .all())
        
        goals = [appearance.goals2 for appearance in appearances if appearance.goals2 is not None]
        pass_accuracies = [appearance.pass_accuracy_in_percent for appearance in appearances if appearance.pass_accuracy_in_percent is not None]
        tackles_won = [appearance.number_of_tackles for appearance in appearances if appearance.number_of_tackles is not None]
        assists = [appearance.assists for appearance in appearances if appearance.assists is not None]
        shots = [appearance.shots for appearance in appearances if appearance.shots is not None]
        successful_dribbles = [appearance.successful_dribbling for appearance in appearances if appearance.successful_dribbling is not None]
        blocks = [appearance.blocks for appearance in appearances if appearance.blocks is not None]
        touches = [appearance.touches for appearance in appearances if appearance.touches is not None]
        yellow_cards = [appearance.yellow_card for appearance in appearances if appearance.yellow_card is not None]
        red_cards = [appearance.red_card for appearance in appearances if appearance.red_card is not None]
        shots_on_target = [appearance.shots_on_target for appearance in appearances if appearance.shots_on_target is not None]
        
        avg_metrics = [
            sum(goals) / len(appearances) if appearances else 0,
            sum(pass_accuracies) / len(appearances) if appearances else 0,
            sum(tackles_won) / len(appearances) if appearances else 0,
            sum(assists) / len(appearances) if appearances else 0,
            sum(shots) / len(appearances) if appearances else 0,
            sum(successful_dribbles) / len(appearances) if appearances else 0,
            sum(blocks) / len(appearances) if appearances else 0,
            sum(touches) / len(appearances) if appearances else 0,
            sum(yellow_cards) / len(appearances) if appearances else 0,
            sum(red_cards) / len(appearances) if appearances else 0,
            sum(shots_on_target) / len(appearances) if appearances else 0,
        ]
        
        team_name = session.query(DimClub.name).filter(DimClub.club_id == team_id).scalar()
        team_names.append(team_name)
        team_metrics.append(avg_metrics)
    
    categories = ['Goals per Game', 'Pass Accuracy', 'Tackles Won per Game', 'Assists per Game', 'Shots per Game',
                  'Successful Dribbles per Game', 'Blocks per Game', 'Touches per Game',
                  'Yellow Cards per Game', 'Red Cards per Game', 'Shots on Target per Game']
    
    return team_names, categories, team_metrics

def display_team_comparison_metrics(team_names, categories, team_metrics):
    data = {'Metric': categories,
            team_names[0]: team_metrics[0],
            team_names[1]: team_metrics[1]}
    
    df = pd.DataFrame(data)
    
    # Hervorhebung der besseren Werte
    def highlight_better(x):
        color = 'background-color: lightgreen' if x[team_names[0]] > x[team_names[1]] else 'background-color: lightcoral' if x[team_names[0]] < x[team_names[1]] else ''
        return [f'background-color: lightgray' if pd.isna(val) else color for val in x]
    
    df = df.style.apply(highlight_better, axis=1)
    
    st.dataframe(df)