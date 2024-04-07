from datetime import datetime
from sqlalchemy import and_
import pandas as pd
from utils.ORM_model import DimPlayer

def calculate_age(birth_date_str):
    if not birth_date_str:
        return "Unbekannt"
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def get_basic_filtered_players(session, min_age, max_age, feet, position, min_value, max_value, contract_expiration_str,
                               min_defensive_contribution=None, min_passing_efficiency=None,
                               min_goal_contribution=None, min_dribbling_ability=None,
                               min_shot_efficiency=None, min_discipline=None,
                               min_involvement=None, min_overall_rating=None):
    query = session.query(DimPlayer)

    if min_age is not None and max_age is not None:
        max_birth_date = datetime(datetime.today().year - min_age, datetime.today().month, datetime.today().day).date()
        min_birth_date = datetime(datetime.today().year - max_age, datetime.today().month, datetime.today().day).date()
        query = query.filter(and_(DimPlayer.date_of_birth <= max_birth_date, DimPlayer.date_of_birth >= min_birth_date))
    

    if feet:
        query = query.filter(DimPlayer.foot.in_(feet))

    if position:
        query = query.filter(DimPlayer.position == position)

    if min_value is not None:
        query = query.filter(DimPlayer.market_value_in_eur >= min_value)
    
    if max_value is not None:
        query = query.filter(DimPlayer.market_value_in_eur <= max_value)

    if contract_expiration_str:
        expiration_date = datetime.strptime(contract_expiration_str, "%Y-%m-%d %H:%M:%S").date()
        query = query.filter(DimPlayer.contract_expiration_date <= expiration_date)


    # Neue Filterbedingungen
    if min_defensive_contribution is not None:
        query = query.filter(DimPlayer.defensive_contribution >= min_defensive_contribution)
    if min_passing_efficiency is not None:
        query = query.filter(DimPlayer.passing_efficiency >= min_passing_efficiency)
    if min_goal_contribution is not None:
        query = query.filter(DimPlayer.goal_contribution >= min_goal_contribution)
    if min_dribbling_ability is not None:
        query = query.filter(DimPlayer.dribbling_ability >= min_dribbling_ability)
    if min_shot_efficiency is not None:
        query = query.filter(DimPlayer.shot_efficiency >= min_shot_efficiency)
    if min_discipline is not None:
        query = query.filter(DimPlayer.discipline >= min_discipline)
    if min_involvement is not None:
        query = query.filter(DimPlayer.involvement >= min_involvement)
    if min_overall_rating is not None:
        query = query.filter(DimPlayer.overall_rating >= min_overall_rating)

    player_data = [{
        'Name': player.name,
        'Alter': calculate_age(player.date_of_birth) if player.date_of_birth else 'Unbekannt',
        'Verein': player.current_club_name,
        'Position': player.position,
        'Fuß': player.foot,
        'Größe': player.height_in_cm,
        'Marktwert': player.market_value_in_eur,
        'Vertragsauslaufzeit': datetime.strptime(player.contract_expiration_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d') if isinstance(player.contract_expiration_date, str) else player.contract_expiration_date.strftime('%Y-%m-%d') if player.contract_expiration_date is not None else 'Unbekannt',
        'Agent': player.agent_name,
        # Hier kannst du weitere Spielerattribute hinzufügen
    } for player in query.all()]

    return pd.DataFrame(player_data)
