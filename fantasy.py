import json

from yahoo_oauth import OAuth2

base_url = 'https://fantasysports.yahooapis.com/fantasy/v2'

league_id = 'nba.l.178155'
first_game_week = 2
current_game_week = 8

# get stat_id => stat_name
id_to_stat = {
    '9004003': 'FGM/A*',
    '5': 'FG%',
    '9007006': 'FTM/A*',
    '8': 'FT%',
    '10': '3PTM',
    '12': 'PTS',
    '15': 'REB',
    '16': 'AST',
    '17': 'ST',
    '18': 'BLK',
    '19': 'TO'
}

cats = [
    'FG%',
    'FT%',
    '3PTM',
    'PTS',
    'REB',
    'AST', 
    'ST',
    'BLK',
    'TO'
]

def get_teams(oauth: OAuth2) -> dict:
    teams_raw = json.loads(oauth.session.get(f'{base_url}/league/{league_id}/teams?format=json').text)
    teams = []
    for team in list(teams_raw['fantasy_content']['league'][1]['teams'].values())[:-1]: # dict has # teams as last element
        teams.append({
            'key': team['team'][0][0]['team_key'],
            'name': team['team'][0][2]['name']
        })
    return teams

def hydrate_stats(oauth: OAuth2, teams: dict) -> None:
    for team in teams:
        team['stats'] = []
        for week in range(2, current_game_week+1): # we missed the first week
            stats_raw = json.loads(oauth.session.get(f'{base_url}/team/{team["key"]}/stats;type=week;week={week}?format=json').text)
            weekly_stats = {}
            for stat in stats_raw['fantasy_content']['team'][1]['team_stats']['stats']:
                if stat['stat']['stat_id'] in id_to_stat:
                    weekly_stats[id_to_stat[stat['stat']['stat_id']]] = stat['stat']['value']
            team['stats'].append(weekly_stats)

def score_team_cats(team1: dict, team2: dict, start_week: int, end_week: int) -> (float, float):
    """Returns the number of categories each team won in the given week range [start_week, end_week]. Ties count as 0.5

    Args:
        team1 (dict): Team to calculate category victories for
        team2 (dict): Team to calculate category victories against
        start_week (int): fantasy week number to start the calculation from
        end_week (int): fantasy week number to end the calculation at (inclusive)

    Returns:
        float: Number of categories team1 won
        float: Number of categories team2 won
    """
    # weekly_attrition_rate = 0.05
    
    points = 0
    for week in range(start_week, end_week + 1): # +1 to make range inclusive
        weekly_points = score_week(team1, team2, week)
        points += weekly_points # * (1 - (end_week - week) * weekly_attrition_rate) # TODO fix value of second teams points per attrition
    return (points, (end_week - start_week + 1) * 9 - points)

def score_team_wins(team1: dict, team2: dict, start_week: int, end_week: int) -> float:
    points = 0
    for week in range(start_week, end_week + 1):
        weekly_points = score_week(team1, team2, week)
        if weekly_points > 4.5:
            points += 3
        elif weekly_points == 4.5:
            points += 1
    return points

def score_week(team1: dict, team2: dict, week: int) -> float:
    week_index_adjust = week - first_game_week
    points = 0
    for cat in cats[:-1]: # skip turnovers
        if float(team1['stats'][week_index_adjust][cat]) > float(team2['stats'][week_index_adjust][cat]):
            points += 1
        elif float(team1['stats'][week_index_adjust][cat]) == float(team2['stats'][week_index_adjust][cat]):
            points += 0.5
    if int(team1['stats'][week_index_adjust]['TO']) < int(team2['stats'][week_index_adjust]['TO']):
        points += 1
    elif int(team1['stats'][week_index_adjust]['TO']) == int(team2['stats'][week_index_adjust]['TO']):
        points += 0
    return points

def print_rankings(team_points: list[dict]):
    teams_by_points = sorted(team_points, key=lambda k: k['points'], reverse=True)
    for i, team in enumerate(teams_by_points):
        print(f'{i+1}. {team["name"]:24s} {team["points"]:.2f}')
        
    for i, team in enumerate(teams_by_points):
        print(f'{i+1}. {team["name"]} ({team["points"]:.2f})')

if __name__ == '__main__':
    oauth = OAuth2(None, None, from_file='./creds.json')
    if not oauth.token_is_valid():
        oauth.refresh_access_token()
     
    # get list of teams
    # teams = get_teams(oauth)
    
    # get stats for each team
    # hydrate_stats(oauth, teams)
    # with open(file='stats.json', mode='w', encoding='utf8') as fp:
    #     json.dump(teams, fp)
    
    # score teams per stat - simple ranking first, then try weighting ranks?
    with open(file='stats.json', mode='r', encoding='utf8') as fp:
        team_stats = json.load(fp)
    
    # calculate number of cats won
    team_expected_points = []
    for i, team1 in enumerate(team_stats):
        points = 0
        for j, team2 in enumerate(team_stats):
            if i == j: continue
            points += score_team_cats(team1, team2, current_game_week, current_game_week)[0]
        team_expected_points.append({
            'name': team1['name'],
            'points': points / (current_game_week - (current_game_week) + 1) / 7 # TODO attrition
        })
    print_rankings(team_expected_points)
    
    # calculate by points 3w, 1t, 0l
    