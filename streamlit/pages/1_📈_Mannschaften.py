import streamlit as st
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
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

def get_team_playstyle(session, selected_team_name):
    """Gets the playstyle of the selected team."""
    # Here you can implement logic to determine the playstyle based on various factors
    return "Offensiv"  # Placeholder value

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

def main():
    st.set_page_config(layout='wide')
    st.title("Mannschaftsauswertung")
    
    with Session() as session:
        teams = session.query(DimClub.name, DimClub.club_id).all()
        team_options = {name: club_id for name, club_id in teams}
        selected_team_name = st.selectbox("Wähle eine Mannschaft", options=list(team_options.keys()))

        tab1, tab2, = st.tabs(["Mannschaft", "H2H"])
        with tab1:
            if selected_team_name:
                selected_team_id = team_options[selected_team_name]
                club_info = get_club_info(session, selected_team_name)

                if club_info:
                    st.subheader(f"Vereinsinformationen für {selected_team_name}")
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.metric("Kadergröße", str(club_info.squad_size))
                    
                    net_transfer_value = club_info.net_transfer_record.strip().replace('€', '').replace('m', ' Mio').replace('k', ' K').replace('+', '').replace('-', '')
                    if '-' in club_info.net_transfer_record:
                        col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Verlust", delta_color="inverse") 
                    else:
                        col2.metric("Transferbilanz", f"€ {net_transfer_value}", "Gewinn", delta_color="normal")
                    
                    ### First ROW
                    col3.metric("Anteil Legionäre (%)", f"{float(club_info.foreigners_percentage)} %")
                    col4.metric("Durchschnittsalter", float(club_info.average_age))
                    total_market_value = get_club_total_market_value(session, selected_team_id)
                    formatted_market_value = '{:,.2f} Mio'.format(total_market_value / 1000000) if total_market_value >= 1000000 else '{:,.2f}'.format(total_market_value)
                    col5.metric("Teamwert", f"€ {formatted_market_value}")  
                    col6.metric("A-Nationalspieler", club_info.national_team_players)
                    
                    
                    #### NEXT ROW
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    st.subheader(f"Vereinsinformationen für {selected_team_name}")
                    col1.metric("aktuelle Form", evaluate_team_form(session, selected_team_name))
                    col2.metric("Spielstil", get_team_playstyle(session, selected_team_name))
                    col3.metric("Punkteschnitt", calculate_league_average_points(session, selected_team_name))
                    col4.metric("bevorzugte Aufstellung", get_preferred_formation_by_team_name(session, selected_team_name))
                    col5.metric("x", calculate_average_xg_per_game(session, selected_team_name))
                    col6.metric("Punkteschnitt", "nein")
                # Spalten für Spielerinformationen und Top Scorer Diagramm
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Spielerinformationen")
                    players = get_players_by_team(session, selected_team_name)
                    df_players = create_players_df(players)
                    # Scrollbare Tabelle für die Spielerinformationen
                    st.write(df_players, use_container_width=True)   
                with col2:
                    st.subheader("Top 10 Scorer")
                    top_scorers_df = get_top_scorers(session, selected_team_id)
                    if not top_scorers_df.empty:
                        plot_top_scorers_bar(top_scorers_df)
                    else:
                        st.write("Keine Daten über die Top Scorer verfügbar.")
                
                st.subheader("Spielperfomance über die Saison")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    plot_points_over_season(session, selected_team_name)
                with col2:
                    plot_goal_effectiveness(session, selected_team_name)
                with col3:
                    plot_game_outcomes(session, selected_team_name)
        with tab2:
            # Streamlit App
            st.title('Radar Chart Beispiel')
            
            team_names = ['Team A', 'Team B']
            categories = ['Tore', 'Gegentore', 'Ballbesitz', 'Passgenauigkeit', 'Torschüsse', 'Dribblings', 'Zweikämpfe', 'Laufleistung']
            values = [
                [2, 1, 60, 80, 15, 10, 40, 12000],
                [3, 0, 55, 85, 20, 8, 45, 12500]
            ]
            fig = create_radar_chart(team_names, categories, values)
            
            st.plotly_chart(fig)
            
if __name__ == '__main__':
    main()
