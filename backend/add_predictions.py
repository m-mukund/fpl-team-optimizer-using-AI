import joblib
from datetime import datetime, timezone
import requests
from preprocessing import fetch_data_new1
import psycopg2 
import pandas as pd

# Database connection (adjust credentials)
def get_db_connection():
    conn = psycopg2.connect(
        host="postgres-service",
        database="postgres",
        user="postgres",
        password="mukund"
    )
    return conn

def get_gameweek(events):
    now = datetime.now(timezone.utc)  # Get the current time in UTC
    for i, event in enumerate(events):
        deadline = datetime.fromisoformat(event["deadline_time"].replace("Z", "+00:00"))
        if not event.get("finished", False):
            if now < deadline:
                return event
            # If current time is past the deadline, return the next gameweek
            elif i + 1 < len(events):
                return events[i + 1]
    return None



#Load prediction model
pred_model= joblib.load('Point_Prediction_model.pkl') 
# Get GW number
fpl_url="https://fantasy.premierleague.com/api/bootstrap-static/"
fpl_data=requests.get(fpl_url)
fpl_json=fpl_data.json()

gw=get_gameweek(fpl_json["events"])["id"]

gw_url = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2024-25/gws/merged_gw.csv"
players_url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2024-25/players_raw.csv"
fixtures_url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2024-25/fixtures.csv"
teams_url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2024-25/teams.csv"


conn = get_db_connection()
cursor = conn.cursor()

sql1 = '''select * from players;'''
cursor.execute(sql1) 
for position, player_id, web_name, cost in cursor.fetchall(): 
    player_df=fetch_data_new1(gw_url, players_url, fixtures_url, teams_url, gw, player_id, web_name)
    player_df=player_df.drop(['name_x', 'total_points', 'web_name', 'fixture'], axis=1)
    if player_df.tail(1).isnull().values.any():
        print("The DataFrame contains null values.")
        prediction=[0.0]
    else:
        prediction=pred_model.predict(player_df.tail(1))
    print(web_name)
    print(prediction)

    insert_query="INSERT INTO expected_points (player_id, position, cost, expected_points, gameweek) VALUES (%s, %s, %s, %s, %s)"
    values=(player_id, position, cost, prediction[0], gw)
    cursor.execute(insert_query, values)
    conn.commit()

print("Added Predictions to database")
