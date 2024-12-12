from flask import Flask, request, jsonify
import pandas as pd
import joblib
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS
import json
from datetime import datetime, timezone
import requests
import redis

app = Flask(__name__)
redis_client = redis.StrictRedis(host='34.171.59.99', port=6379, db=0, decode_responses=True)

# Enable CORS for all routes or specific origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Position and budget constraints
POSITION_LIMITS = {
    "GK": 1,
    "DEF": 4,
    "MID": 4,
    "FWD": 2
}
TOTAL_BUDGET = 100

# # Load pre-trained model
# model = joblib.load("fpl_model.pkl")

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

def get_optimal_transfer_with_constraints(current_team, gameweek, remaining_budget):
    try:
        # Connect to the PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        optimal_transfer = None
        max_improvement = float("-inf")
        
        # Loop through each player in the team
        for player in current_team:
            player_id = player["player_id"]
            
            # Fetch player details from the expected_points table
            sql1 = '''
            SELECT position, cost, expected_points 
            FROM expected_points 
            WHERE player_id = %(player_id)s AND gameweek = %(gameweek)s;
            '''
            cursor.execute(sql1, {"player_id": player_id, "gameweek": gameweek})
            result = cursor.fetchone()
            
            if not result:
                continue  # Skip if the player doesn't have data for the given gameweek
            
            player_position = result["position"]
            player_cost = result["cost"]
            player_points = result["expected_points"]
            
            # Calculate the maximum budget available for a replacement
            max_budget = remaining_budget + player_cost
            
            # Query to find the best replacement
            query = """
            SELECT 
                ep.player_id, 
                ep.position, 
                ep.cost, 
                ep.expected_points AS points,
                p.web_name
            FROM expected_points ep
            JOIN players p ON ep.player_id = p.id
            WHERE 
                ep.position = %(position)s
                AND ep.player_id NOT IN %(current_team_ids)s
                AND ep.cost <= %(max_budget)s
                AND ep.gameweek = %(gameweek)s
            ORDER BY points DESC
            LIMIT 1;
            """
            cursor.execute(query, {
                "position": player_position,
                "current_team_ids": tuple(p["player_id"] for p in current_team),
                "max_budget": max_budget,
                "gameweek": gameweek
            })
            
            replacement = cursor.fetchone()
            
            # Calculate the improvement in points
            if replacement:
                improvement = replacement["points"] - player_points
                if improvement > max_improvement:
                    max_improvement = improvement
                    optimal_transfer = {
                        "outgoing_player": player,
                        "incoming_player": replacement,
                        "improvement": improvement
                    }
        
        cursor.close()
        conn.close()

        return optimal_transfer

    except Exception as e:
        print(f"Error: {e}")
        return None
    
# Define the queries for each position
def get_top_players(cursor, position, max_budget, gameweek, limit):
    query = f"""
    SELECT 
        ep.player_id,
        p.web_name
    FROM expected_points ep
    JOIN players p ON ep.player_id = p.id
    WHERE 
        ep.position = %s
        AND ep.cost <= %s
        AND ep.gameweek = %s
    ORDER BY ep.expected_points DESC
    LIMIT %s;
    """
    cursor.execute(query, (position, max_budget, gameweek, limit))
    team= cursor.fetchall()
    print("in get")
    print(team)
    team_dict = [dict(row) for row in team]
    return team_dict

def calculate_best_team(cursor,max_budget, gameweek):
    team = []
    # Fetch top 4 defenders
    defenders = get_top_players(cursor, 'DEF', max_budget, gameweek, 4)
    team.extend(defenders)

    # Fetch top 4 midfielders
    midfielders = get_top_players(cursor, 'MID', max_budget, gameweek, 4)
    team.extend(midfielders)

    # Fetch top 2 forwards
    forwards = get_top_players(cursor, 'FWD', max_budget, gameweek, 2)
    team.extend(forwards)
    print("in calc")
    print(team)
    plain_team = [dict(row) for row in team]

    return {"success": True, "best_team": {"players": plain_team}}

# Function to get cached best team or calculate and cache it
def get_cached_best_team(gameweek):

    # Connect to the PostgreSQL database
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    max_budget=1000


    cache_key = f"best_team{gameweek}"  # Use a unique key based on params

    # Try to get the best team from the cache
    cached_team = redis_client.get(cache_key)

    if cached_team:
        print("Returning cached best team", flush=True)
        return json.loads(cached_team)  # Return cached data

    # If not in cache, calculate and cache it
    print("Calculating best team...", flush=True)
    best_team = calculate_best_team(cursor, max_budget, gameweek)

    # Cache the result for 600 seconds (10 minutes)
    redis_client.setex(cache_key, 600, json.dumps(best_team))

    return jsonify(best_team)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])  # Return an empty list if no query

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to find matching player names and their IDs
    cursor.execute("""
        SELECT id, web_name 
        FROM players 
        WHERE web_name ILIKE %s 
        LIMIT 5
    """, (f"%{query}%",))
    
    results = cursor.fetchall()
    for row in results:
        print(row)
    cursor.close()
    conn.close()
    
    # Format results as a list of dictionaries
    players = [{"player_id": row[0], "web_name": row[1]} for row in results]
    return jsonify(players)


@app.route("/predict", methods=["POST"])
def predict():
    data=request.get_json()
    print("Team recieved")
    print(data)
    team=data.get("current_team")
    remaining_budget=data.get("remaining_budget")

    fpl_url="https://fantasy.premierleague.com/api/bootstrap-static/"
    fpl_data=requests.get(fpl_url)
    fpl_json=fpl_data.json()

    gw=get_gameweek(fpl_json["events"])["id"]
    print("GW obtained")

    if not gw:
        return jsonify({"Could not get GW": str(e)}), 500
    
    try:
        optimal_transfer=get_optimal_transfer_with_constraints(team, gw, remaining_budget)
        print(optimal_transfer)
        return jsonify({"success": True, "optimal_transfer": optimal_transfer}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/best_team', methods=['GET'])
def best_team():
    # Connect to the PostgreSQL database
    try:
        fpl_url="https://fantasy.premierleague.com/api/bootstrap-static/"
        fpl_data=requests.get(fpl_url)
        fpl_json=fpl_data.json()
        gameweek=get_gameweek(fpl_json["events"])["id"]
        print("GW obtained", flush=True)

        return get_cached_best_team(gameweek)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    # start flask app
    app.run(host="0.0.0.0", port=8000, debug=True)
