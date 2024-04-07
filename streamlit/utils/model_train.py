from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from ORM_model import DimPlayer, FactAppearance, DimClub
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

# Verbindung zur Datenbank herstellen
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/football_olap_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Funktion zum Berechnen des Spieleralters
def player_age(date_of_birth):
    if date_of_birth:
        return (pd.Timestamp.now() - pd.to_datetime(date_of_birth)).days // 365
    return None

# Alle Spieler aus der Datenbank abrufen, die auch einen Eintrag in den FactAppearance haben
all_players = session.query(DimPlayer).join(FactAppearance).group_by(DimPlayer.player_id).all()

all_player_data = []

for p in all_players:
    p_appearances = session.query(FactAppearance).filter(FactAppearance.player_id == p.player_id).all()
    if p_appearances:
        p_data = {
            'market_value': p.market_value_in_eur,
            'age': player_age(p.date_of_birth),
            'contract_days_remaining': (pd.to_datetime(p.contract_expiration_date) - pd.Timestamp.now()).days if p.contract_expiration_date else None,
            'position': p.position,
            'foot': p.foot,
            'height_in_cm': p.height_in_cm,
            'country_of_citizenship': p.country_of_citizenship,
            'current_club_name': p.current_club_name,
            'assists_per_game': sum(a.assists or 0 for a in p_appearances) / len(p_appearances),
            'minutes_played_per_game': sum(a.minutes_played or 0 for a in p_appearances) / len(p_appearances),
            'goals_per_game': sum(a.goals2 or 0 for a in p_appearances) / len(p_appearances),
            'shots_per_game': sum(a.shots or 0 for a in p_appearances) / len(p_appearances),
            'shots_on_target_per_game': sum(a.shots_on_target or 0 for a in p_appearances) / len(p_appearances),
            'yellow_cards_per_game': sum(a.yellow_card or 0 for a in p_appearances) / len(p_appearances),
            'red_cards_per_game': sum(a.red_card or 0 for a in p_appearances) / len(p_appearances),
            'successful_passes_per_game': sum(a.successful_passes or 0 for a in p_appearances) / len(p_appearances),
            'attempted_passes_per_game': sum(a.attempted_passes or 0 for a in p_appearances) / len(p_appearances),
            'progressive_passes_per_game': sum(a.progressive_passes or 0 for a in p_appearances) / len(p_appearances),
            'carries_per_game': sum(a.carries or 0 for a in p_appearances) / len(p_appearances),
            'progressive_runs_per_game': sum(a.progressive_runs or 0 for a in p_appearances) / len(p_appearances),
            'successful_dribbles_per_game': sum(a.successful_dribbling or 0 for a in p_appearances) / len(p_appearances),
            'attempted_dribbles_per_game': sum(a.attempted_dribbles or 0 for a in p_appearances) / len(p_appearances)
        }
        
        current_club = session.query(DimClub).filter(DimClub.club_id == p.current_club_id).first()
        if current_club:
            p_data['current_club_total_market_value'] = current_club.total_market_value
            p_data['current_club_squad_size'] = current_club.squad_size
            p_data['current_club_average_age'] = current_club.average_age
            p_data['current_club_foreigners_number'] = current_club.foreigners_number
            p_data['current_club_foreigners_percentage'] = current_club.foreigners_percentage
            p_data['current_club_national_team_players'] = current_club.national_team_players
            p_data['current_club_stadium_seats'] = current_club.stadium_seats
        
        all_player_data.append(p_data)

all_player_df = pd.DataFrame(all_player_data)

print(f"Anzahl der Spieler vor der Bereinigung: {len(all_player_df)}")

# DataFrame bereinigen (Zeilen mit fehlenden Werten in der Zielvariable 'market_value' entfernen)
all_player_df = all_player_df.dropna(subset=['market_value'])

print(f"Anzahl der Spieler nach der Bereinigung: {len(all_player_df)}")

# Überprüfen, ob der Datensatz leer ist
if all_player_df.empty:
    raise ValueError("Der bereinigte Datensatz ist leer. Bitte stellen Sie sicher, dass nach der Vorverarbeitung Daten vorhanden sind.")

# Fehlende Werte in 'current_club_total_market_value' durch 0 ersetzen
all_player_df['current_club_total_market_value'] = all_player_df['current_club_total_market_value'].fillna(0)

# Modell trainieren
X = all_player_df.drop('market_value', axis=1)
y = all_player_df['market_value']

# Kategoriale und numerische Features aufteilen
categorical_features = ['position', 'foot', 'country_of_citizenship', 'current_club_name']
numeric_features = [col for col in X.columns if col not in categorical_features]

# Preprocessing Pipelines
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

# Modell-Pipeline
model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(random_state=42))
])

# Hyperparameter-Tuning mit GridSearchCV
param_grid = {
    'regressor__n_estimators': [100, 200, 300],
    'regressor__max_depth': [None, 5, 10],
    'regressor__min_samples_split': [2, 5, 10],
    'regressor__min_samples_leaf': [1, 2, 4]
}

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

grid_search = GridSearchCV(estimator=model, param_grid=param_grid, cv=5, n_jobs=-1, verbose=2)
grid_search.fit(X_train, y_train)

best_model = grid_search.best_estimator_

# Metriken zur Bewertung des Modells berechnen
y_pred = best_model.predict(X_test)
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)

print(f"Best parameters: {grid_search.best_params_}")
print(f"R²-Score: {r2:.2f}")
print(f"MAE: {mae:.2f}")
print(f"MSE: {mse:.2f}")
print(f"RMSE: {rmse:.2f}")

# Modell speichern
joblib.dump(best_model, 'market_value_model.pkl')