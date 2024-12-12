import pandas as pd
import numpy as np
import requests

def extract_fixture_by_event(target_event, id):
    # If input is a JSON string, parse it
    fpl_url="https://fantasy.premierleague.com/api/element-summary/"+str(id)+"/"
    fpl_data=requests.get(fpl_url)
    fpl_json=fpl_data.json()
    
    # Extract fixtures for the specified event
    event_fixtures = [
        fixture for fixture in fpl_json.get('fixtures', []) 
        if fixture.get('event') == target_event
    ]
    
    return event_fixtures[0].get('id')

def fetch_data_new1(url, players_url, fix_url, teams_url, gw, player_id, web_name):

    # Read CSVs
    df = pd.read_csv(url, encoding='utf-8')
    df2 = pd.read_csv(players_url, encoding='utf-8')
    df_fix_raw=pd.read_csv(fix_url)
    df_teams_raw=pd.read_csv(teams_url)

    # Dropping unnecessary columns and creating first_name and last_name for join
    df[['first_name', 'second_name']] = df['name'].str.split(' ', n=1, expand=True)
    df2=df2[['first_name', 'second_name', 'team', 'web_name']]
    df2=df2.loc[df2['web_name']==web_name]
    df_fix=df_fix_raw[['id', 'team_a', 'team_h', 'team_h_difficulty', 'team_a_difficulty']]
    df_teams=df_teams_raw[['name', 'id', 'strength', 'strength_overall_home', 'strength_overall_away', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away']]
    
    # Merging df2 to get team name
    pd.set_option('display.max_columns', None)
    df=pd.merge(df, df2, on=['first_name', 'second_name'], how='inner')
    df['bonus'] = (
    df.groupby('name')['bonus']
    .apply(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
    .reset_index(level=0, drop=True)  # Ensure the index matches the original DataFrame
    )
    # Create a copy of the row of previous GW for a specific player
    gw_row = df[(df['GW'] == (df['GW'].max()))].copy()
    gw_row['GW']=gw
    gw_row['fixture']=extract_fixture_by_event(gw, player_id)
    df=pd.concat([df, gw_row], ignore_index=True)


    teams_away=df_teams[['name', 'id', 'strength', 'strength_overall_away', 'strength_attack_away', 'strength_defence_away']]
    teams_home=df_teams[['name', 'id', 'strength', 'strength_overall_home', 'strength_attack_home', 'strength_defence_home']]

    # Merge for team_a (away team)
    df_fix = df_fix.merge(
    teams_away,
    how='left',
    left_on='team_a',
    right_on='id',
    suffixes=('', '_team_a')
    )

    # Merge for team_h (home team)
    df_fix = df_fix.merge(
    teams_home,
    how='left',
    left_on='team_h',
    right_on='id',
    suffixes=('', '_team_h')
    )

    
    if 'expected_assists' in df.columns:
        df.drop(['expected_assists', 'expected_goal_involvements', 'expected_goals', 'expected_goals_conceded', 'starts'], axis=1, inplace=True)


    # Creating 'form' column which is mean of total points from the last 5 GWs
    df = df.sort_values(by=['name', 'GW'])
    df['form'] = (
    df.groupby('name')['total_points']
    .apply(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
    .reset_index(level=0, drop=True)  # Ensure the index matches the original DataFrame
    )
    df['form'] = df.groupby('name')['form'].transform(lambda x: x.fillna(0))

    columns_to_process = ['minutes', 'goals_scored', 'goals_conceded', 'assists', 'xP']

    df = df.sort_values(by=['name', 'GW'])

    for col in columns_to_process:
        new_col = f'{col}_rolling_avg'  # Create a new column name
        df[new_col] = (
        df.groupby('name')[col]
        .apply(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
        .reset_index(level=0, drop=True)  # Ensure the index matches the original DataFrame
        )
        # Fill NaN values with 0 in the new column
        df[new_col] = df.groupby('name')[new_col].transform(lambda x: x.fillna(0))

    # Taking cummulative stats from the previous GWs
    columns_to_cumsum = ['goals_scored', 'assists', 'yellow_cards', 'clean_sheets', 'goals_conceded']

    # Apply cumulative sum for each column grouping by 'name', excluding the current row


    df.update(
    df.groupby('name')[columns_to_cumsum].transform(lambda x: x.mask(x.index == x.index.min(), 0))
    )


    #Merging fixtures dataframe to get 'fixture difficulty'
    df=pd.merge(df, df_fix, left_on='fixture', right_on='id', how='left')
    
    df['fixture_difficulty']=np.where(df['was_home'], df['team_h_difficulty'], df['team_a_difficulty'])

        # Define a mapping for the positions
    position_mapping = {'GK': 1, 'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}

    # Map the position values to numerical values
    df['position_num'] = df['position'].map(position_mapping)
    
    # Merging teams dataframe to obtain team strength stats
    #df=pd.merge(df, df_teams, left_on='team', right_on='name', how='left')
    df['strength_overall']=np.where(df['was_home'], df['strength_overall_home'], df['strength_overall_away'])
    df['strength_attack']=(np.where(df['was_home'], df['strength_attack_home'], df['strength_attack_away']))
    df['strength_defence']=(np.where(df['was_home'], df['strength_defence_home'], df['strength_defence_away']))
    df['opposition_strength']=np.where(df['was_home'], df['strength_overall_away'], df['strength_overall_home'])
    df['opposition_attack']=(np.where(df['was_home'], df['strength_attack_away'], df['strength_attack_home']))
    df['opposition_defence']=(np.where(df['was_home'], df['strength_defence_away'], df['strength_defence_home']))



    df['clean_sheets_by_position'] = df['clean_sheets'] / df['position_num']
    df=df.drop(['team_h_difficulty', 'team_a_difficulty', 'team_a_score', 'team_h_score', 'opponent_team', 'xP', 'kickoff_time', 'element', 'clean_sheets', 'assists', 'strength_attack', 'strength_defence', 'strength_team_h', 'goals_conceded'], axis=1)
    
    
    merged_df=df.drop(['team_x', 'team_y', 'position', 'GW', 'first_name', 'second_name', 'bps', 'round', 'name_y', 'id', 'minutes', 'own_goals', 'name_team_h', 'team_a', 'team_h', 'id_team_a', 'id_team_h', 'strength_overall_home', 'strength_overall_away', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away', 'transfers_balance', 'saves', 'penalties_missed', 'penalties_saved', 'red_cards', 'yellow_cards', 'strength', 'was_home', 'strength'],axis=1)
    #print(merged_df.columns)


    return merged_df
