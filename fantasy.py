import json

from yahoo_oauth import OAuth2

base_url = 'https://fantasysports.yahooapis.com/fantasy/v2'

league_id = 'nba.l.178155'
first_game_week = 2
current_game_week = 16

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
        print(f'{i+1}. {team["name"]} ({team["points"]:.2f})')

if __name__ == '__main__':
    oauth = OAuth2(None, None, from_file='./creds.json')
    if not oauth.token_is_valid():
        oauth.refresh_access_token()
     
    # get stats for each team
    # teams = get_teams(oauth)
    # hydrate_stats(oauth, teams)
    # with open(file='stats.json', mode='w', encoding='utf8') as fp:
    #     json.dump(teams, fp)
    
    # score teams per stat - simple ranking first, then try weighting ranks?
    with open(file='stats.json', mode='r', encoding='utf8') as fp:
        team_stats = json.load(fp)
    
    # calculate number of cats won
    team_expected_points_per_week = {}
    for team in team_stats:
        team_expected_points_per_week[team['name']] = []
    
    for week in range(first_game_week, current_game_week + 1):
        for i, team1 in enumerate(team_stats):
            points = 0
            for j, team2 in enumerate(team_stats):
                if i == j: continue
                points += score_week(team1, team2, week)
            team_expected_points_per_week[team1['name']].append(points / 7)
    
    # print(json.loads(oauth.session.get(f'{base_url}/team/428.l.178155.t.1/stats;type=week;week=2?format=json').text))
    with open(file='test.json', mode='w', encoding='utf8') as fp:
        json.dump(json.loads(oauth.session.get(f'{base_url}/team/428.l.178155.t.1/matchups?format=json').text), fp)
    # read data for each team + write to file
    
    # SET WEEKS HERE
    start = current_game_week - 5 - first_game_week
    end = current_game_week - first_game_week
    
    team_expected_points = []
    for team, points in team_expected_points_per_week.items():
        team_expected_points.append({
            'name': team,
            'points': sum(points[start:end+1]) / len(points[start:end+1])
        })
    
    # print_rankings(team_expected_points)
    
    
    # TEAM / WEEK RANKINGS
    team_week_points = []
    for team, points in team_expected_points_per_week.items():
        for week, week_points in enumerate(points):
            team_week_points.append({
                'name': f'{team} - Week {week + first_game_week}',
                'points': week_points
            })
    print('\n\n')
    # print_rankings(team_week_points)