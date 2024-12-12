import psycopg2 
import pandas as pd 
from sqlalchemy import create_engine 


conn_string = 'postgresql://postgres:mukund@postgres-service:5432/postgres'
players_url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/refs/heads/master/data/2024-25/players_raw.csv"
gws_url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/refs/heads/master/data/2024-25/gws/merged_gw.csv"

db = create_engine(conn_string) 
conn = db.connect() 


# our dataframe 
players_df=pd.read_csv(players_url)
players_df=players_df[['id', 'first_name', 'second_name', 'web_name', 'now_cost']]

df=pd.read_csv(gws_url)
df[['first_name', 'second_name']] = df['name'].str.split(' ', n=1, expand=True)
df=df[['first_name', 'second_name', 'position']]

# Merging df2 to get team name
# Merge df and players_df on 'first_name' and 'second_name'
merged_df = pd.merge(df, players_df, on=['first_name', 'second_name'], how='inner')

# Keep only the first occurrence of each 'first_name' and 'second_name' from players_df
players_df = merged_df.drop_duplicates(subset=['first_name', 'second_name'])

# Drop the now-unnecessary 'first_name' and 'second_name' columns
players_df = players_df.drop(['first_name', 'second_name'], axis=1)


players_df.to_sql('players', con=conn, if_exists='replace', 
		index=False) 
conn = psycopg2.connect(conn_string 
						) 
conn.autocommit = True
cursor = conn.cursor() 

sql1 = '''select * from players LIMIT 10;'''
cursor.execute(sql1) 
for i in cursor.fetchall(): 
	print(i) 

# conn.commit() 
conn.close() 


# CREATE TABLE player_expected_points (
#     player_id INT,              -- Player ID
#     gameweek INT,               -- Gameweek number
#     expected_points NUMERIC,    -- Expected points for this gameweek
#     PRIMARY KEY (player_id, gameweek)
# );

# CREATE TABLE expected_points (
#     player_id INT NOT NULL,         -- Unique identifier for the player
#     position VARCHAR(50) NOT NULL, -- Position of the player (e.g., Forward, Midfielder)
#     cost DECIMAL(10, 2) NOT NULL,  -- Cost of the player in the game, with two decimal places
#     expected_points DECIMAL(10, 2) NOT NULL, -- Expected points for the player
#     gameweek INT NOT NULL,         -- Gameweek number
#     PRIMARY KEY (player_id, gameweek) -- Ensures unique entries for a player per gameweek
# );