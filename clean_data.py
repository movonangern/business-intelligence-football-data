from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ENV import DATABASE_URL

BASE_PATH = 'data/OLAP data'

Base = declarative_base()

class DimCompetition(Base):
    __tablename__ = 'dim_competition'
    competition_id = Column(String(50), primary_key=True)
    competition_code = Column(String(50))
    name = Column(String(50))
    sub_type = Column(String(50))
    type = Column(String(50))
    country_id = Column(Integer)
    contry_name = Column(String(50))
    domestic_league_code = Column(String(50))
    confederation = Column(String(50))
    url = Column(String(200))

class DimClub(Base):
    __tablename__ = 'dim_clubs'
    club_id = Column(Integer, primary_key=True)
    club_code = Column(String(50))
    name = Column(String(100))
    domestic_competition_id = Column(String(100), ForeignKey('dim_competition.competition_id'))
    competition = relationship("DimCompetition", backref="clubs", lazy="select")
    total_market_value = Column(Integer)
    squad_size = Column(Integer)
    average_age = Column(Integer)
    foreigners_number = Column(Integer)
    foreigners_percentage = Column(Integer)
    national_team_players = Column(Integer)
    stadium_name = Column(String(50))
    stadium_seats = Column(Integer)
    net_transfer_record = Column(String(50))
    coach_name = Column(String(50))
    last_season = Column(Integer)
    filename = Column(String(100))
    url = Column(String(100))

class DimPlayer(Base):
    __tablename__ = 'dim_players'
    player_id = Column(Integer, primary_key=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    name = Column(String(100))
    last_season = Column(Integer)
    current_club_id = Column(Integer, ForeignKey('dim_clubs.club_id'))
    club = relationship("DimClub", backref="players", lazy="select")
    player_code = Column(String(50))
    country_of_birth = Column(String(50))
    city_of_birth = Column(String(100))
    country_of_citizenship = Column(String(50))
    date_of_birth = Column(String(50))
    sub_position = Column(String(50))
    position = Column(String(50))
    foot = Column(String(50))
    height_in_cm = Column(Integer)
    contract_expiration_date = Column(String(50))
    agent_name = Column(String(50))
    image_url = Column(String(200))
    url = Column(String(200))
    current_club_domestic_competition_id = Column(String(100), ForeignKey('dim_competition.competition_id'))
    competition = relationship("DimCompetition", backref="players", lazy="select")
    current_club_name = Column(String(100))
    market_value_in_eur = Column(Integer)
    highest_market_value_in_eur = Column(Integer)
    goal_contribution = Column(Float)
    defensive_contribution = Column(Float)
    passing_efficiency = Column(Float)
    dribbling_ability = Column(Float)
    shot_efficiency = Column(Float)
    discipline = Column(Float)
    involvement = Column(Float)
    overall_rating = Column(Float) 
    
class DimGame(Base):
    __tablename__ = 'dim_games'
    game_id = Column(Integer, primary_key=True)
    competition_id = Column(String(100), ForeignKey('dim_competition.competition_id'))
    competition = relationship("DimCompetition", backref="games", lazy="select")
    season = Column(Integer)
    round = Column(String(50))
    date = Column(String(50))
    home_club_id = Column(Integer, ForeignKey('dim_clubs.club_id'))
    home_club = relationship("DimClub", backref="home_games", foreign_keys=[home_club_id], lazy="select")
    away_club_id = Column(Integer, ForeignKey('dim_clubs.club_id'))
    away_club = relationship("DimClub", backref="away_games", foreign_keys=[away_club_id], lazy="select")
    home_club_goals = Column(Integer)
    away_club_goals = Column(Integer)
    home_club_position = Column(Integer)
    away_club_position = Column(Integer)
    home_club_manager_name = Column(String(50))
    away_club_manager_name = Column(String(50))
    stadium = Column(String(100))
    attendance = Column(Integer)
    referee = Column(String(50))
    url = Column(String(200))
    home_club_formation = Column(String(50))
    away_club_formation = Column(String(50))
    home_club_name = Column(String(500))
    away_club_name = Column(String(1000))
    aggregate = Column(String(50))
    competition_type = Column(String(50))
    
    
class FactAppearance(Base):
    __tablename__ = 'fact_appearances'
    appearance_id = Column(String(100), primary_key=True)
    game_id = Column(Integer, ForeignKey('dim_games.game_id'))
    game = relationship("DimGame", backref="appearances", lazy="select")
    player_id = Column(Integer, ForeignKey('dim_players.player_id'))
    player = relationship("DimPlayer", backref="appearances", lazy="select")
    player_club_id = Column(Integer, ForeignKey('dim_clubs.club_id'))
    club = relationship("DimClub", backref="appearances", foreign_keys=[player_club_id], lazy="select")
    player_current_club_id = Column(Integer, ForeignKey('dim_clubs.club_id'))
    current_club = relationship("DimClub", backref="current_club_appearances", foreign_keys=[player_current_club_id], lazy="select")
    date = Column(String(50))
    player_name = Column(String(50))
    competition_id = Column(String(100), ForeignKey('dim_competition.competition_id'))
    competition = relationship("DimCompetition", backref="appearances", lazy="select")
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    goals1 = Column(Integer)
    assists = Column(Integer)
    minutes_played = Column(Integer)
    goals2 = Column(Integer)
    assets = Column(Integer)
    converted_penalties = Column(Integer)
    attempted_penalty = Column(Integer)
    shots = Column(Integer)
    shots_on_target = Column(Integer)
    yellow_card = Column(Integer)
    red_card = Column(Integer)
    touches = Column(Integer)
    number_of_tackles = Column(Integer)
    ball_win = Column(Integer)
    blocks = Column(Integer)
    expected_goals = Column(Integer)
    expected_goals_without_penalties = Column(Integer)
    expected_goal_assists = Column(Integer)
    shot_attempt = Column(Integer)
    goal_assists = Column(Integer)
    successful_passes = Column(Integer)
    attempted_passes = Column(Integer)
    pass_accuracy_in_percent = Column(Integer)
    progressive_passes = Column(Integer)
    carries = Column(Integer)
    progressive_runs = Column(Integer)
    attempted_dribbles = Column(Integer)
    successful_dribbling = Column(Integer)

engine = create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Einträge finden, bei denen goals2 None ist
appearances_to_delete = session.query(FactAppearance).filter(FactAppearance.goals2 == None).all()

# Batchgröße definieren
batch_size = 10000

# Löschen von Einträgen aus der fact_appearances Tabelle in Batches
for i in range(0, len(appearances_to_delete), batch_size):
    appearances_batch = appearances_to_delete[i:i+batch_size]
    for appearance in appearances_batch:
        session.delete(appearance)
    session.commit()