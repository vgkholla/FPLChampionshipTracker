import dryscrape
import operator
import os

from bs4 import BeautifulSoup
from ConfigParser import SafeConfigParser

class Config(object):
    """Contains all the configuration and provides easy API access"""

    PLAYERS_SECTION = 'Players'
    TEAMS_SECTION = 'Teams'
    REQUIRED_SECTIONS = [ PLAYERS_SECTION, TEAMS_SECTION ]

    def __init__(self, configFile):
        self.config = SafeConfigParser()
        self.config.read(configFile)
        for required_section in self.REQUIRED_SECTIONS:
            if not self.config.has_section(required_section):
                raise Exception('Required section [' + required_section + '] does not exist')

    def get_player_id(self, name):
        if not self.config.has_option(self.PLAYERS_SECTION, name):
            raise Exception('Player [' + name + '] does not exist')
        return self.config.getint(self.PLAYERS_SECTION, name)

    def get_team(self, name):
        if not self.config.has_option(self.TEAMS_SECTION, name):
            raise Exception('Team [' + name + '] does not exist')
        return self.config.get(self.TEAMS_SECTION, name).split(',')

    def get_players(self):
        return self.config.options(self.PLAYERS_SECTION)

    def get_teams(self):
        return self.config.options(self.TEAMS_SECTION)

class Player(object):
    """Represents a player and all associated details"""

    SOUP_PARSER = 'html.parser'
    BASE_URL = 'http://fantasy.premierleague.com/a/entry/'
    SESSION = dryscrape.Session(base_url = BASE_URL)
    HISTORY_SUFFIX = '/history'

    POINTS_DIV_ID = 'ismr-event-history'
    TABLE_TAG = 'table'
    POINTS_TABLE_ATTR = {'class':'ism-table'}
    TABLE_BODY_TAG = 'tbody'
    TABLE_ROW_TAG = 'tr'
    TABLE_COL_TAG = 'td'
    OVERALL_POINTS_COL = 6

    def __init__(self, name, team, config):
        self.name = name
        self.id = config.get_player_id(name)
        self.team = team
        self.load_data()

    def __repr__(self):
        return str(self.id)

    def __str__(self):
        return self.name + ' (' + str(self.id) + '): Points - ' + str(self.gw_points)

    def load_data(self):
        url = str(self.id) + self.HISTORY_SUFFIX
        self.SESSION.visit(url)
        if self.SESSION.status_code() is not 200:
            raise Exception('Could not GET ' + url)
        self.soup = BeautifulSoup(self.SESSION.body(), self.SOUP_PARSER)
        gameweeks = self.soup.find(id = self.POINTS_DIV_ID).find(self.TABLE_TAG, attrs = self.POINTS_TABLE_ATTR).find(self.TABLE_BODY_TAG).find_all(self.TABLE_ROW_TAG)
        self.gw_points = []
        overall = 0
        for gameweek in gameweeks:
            cur_overall = int(gameweek.find_all(self.TABLE_COL_TAG)[self.OVERALL_POINTS_COL].text)
            self.gw_points.append(cur_overall - overall)
            overall = cur_overall

    def get_points_for_all_gws(self):
        return self.gw_points

    def get_points_for_gw(self, gameweek):
        if gameweek <= 0 or gameweek > len(self.gw_points):
            raise Exception('Data for GW-' + gameweek + ' does not exist')
        return self.gw_points[gameweek - 1]

    def get_team(self):
        return self.team

class Team(object):
    """Represents a team and contains all the players of the team"""
    def __init__(self, name, config):
        self.name = name
        self.players = {}
        for player in config.get_team(name):
            self.players[player] = Player(player, self, config)
        self.points = 0
        self.calculate_averages()

    def __repr__(self):
        representation = self.name
        for player in self.players:
            representation = representation + ' ' + repr(player)
        return representation

    def __str__(self):
        string = self.name + ' : '
        for player in self.players:
            string = string + ' ' + str(player)
        return string

    def calculate_averages(self):
        self.team_averages_by_gw = []
        for player in self.players:
            player_points = self.players[player].get_points_for_all_gws()
            for i in xrange(len(player_points)):
                if i >= len(self.team_averages_by_gw):
                    self.team_averages_by_gw.append(player_points[i])
                else:
                    self.team_averages_by_gw[i] = self.team_averages_by_gw[i] + player_points[i]
        total = 0
        for i in xrange(len(self.team_averages_by_gw)):
            self.team_averages_by_gw[i] = float(self.team_averages_by_gw[i]) / float(len(self.players))
            total = total + self.team_averages_by_gw[i]
        self.total_average = total / len(self.team_averages_by_gw)

    def is_member(self, player_name):
        return player_name in self.players

    def get_player_by_name(self, player_name):
        player = self.players.get(player_name, None)
        if player is None:
            raise Exception('Player ' + player_name + ' does not exist in ' + self.name)
        return player

    def get_players(self):
        return self.players

    def get_total_team_average(self):
        return self.total_average

    def get_team_averages_by_gw_by_gw(self):
        return self.team_averages_by_gw

    def get_team_average_for_gw(self, gameweek):
        if gameweek <= 0 or gameweek > len(self.team_averages_by_gw):
            raise Exception('Data for GW-' + gameweek + ' does not exist')
        return self.team_averages_by_gw[gameweek - 1]

    def get_players_sorted_by_points_for_gw(self, gameweek):
        if gameweek <= 0 or gameweek > len(self.team_averages_by_gw):
            raise Exception('Data for GW-' + gameweek + ' does not exist')
        points = {}
        for player in self.players.items():
            points[player] = player[1].get_points_for_gw(gameweek)
        return sorted(points.items(), key=operator.itemgetter(1), reverse=True) 

    def add_points(self, points):
        self.points = self.points + points
        return self.points

    def get_points(self):
        return self.points
        
if __name__ == '__main__':
    MAX_SUM_PLAYER_COUNT = 2
    MAX_POSITION_FOR_AWARD = 3

    GW_MAX_AVERAGE_BONUS = 5
    GW_MAX_SUM_BONUS = 2
    POSITIONS_AWARDS = { 1 : 3, 2 : 2, 3 : 1} 

    dir_name = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_name, 'game.config')
    config = Config(config_path)

    teams = []
    players = []
    for team in config.get_teams():
        team_obj = Team(team, config)
        for player in team_obj.get_players().items():
            players.append(player[1])
        teams.append(team_obj)

    winners_by_gw = {}
    top_three_every_gw = {}
    max_top_sum = 0
    max_top_teams = []

    # determine team(s) that wins in each game week
    # determine the team(s) that has the max sum for MAX_SUM_PLAYER_COUNT members
    for team in teams:
        if len(team.get_players()) < MAX_SUM_PLAYER_COUNT:
            raise Exception(team.name + ' does not have enough players to calculate max top invidual players sum')
        averages_by_gw = team.get_team_averages_by_gw_by_gw()
        for i in xrange(len(averages_by_gw)):
            if i not in winners_by_gw or winners_by_gw[i][0] < averages_by_gw[i]:
                winners_by_gw[i] = (averages_by_gw[i], [team])
            elif winners_by_gw[i][0] == averages_by_gw[i]:
                winners_by_gw[i][1].append(team)
        players_sorted_by_points = team.get_players_sorted_by_points_for_gw(i + 1);
        top_players_sum = 0
        for i in xrange(MAX_SUM_PLAYER_COUNT):
            top_players_sum = top_players_sum + players_sorted_by_points[i][1]
        if top_players_sum == max_top_sum:
            max_top_teams.append(team)
        elif top_players_sum > max_top_sum:
            max_top_sum = top_players_sum
            max_top_teams = [team]

    # add points to the team(s) that have the max sum for MAX_SUM_PLAYER_COUNT members
    for team in max_top_teams:
        team.add_points(GW_MAX_SUM_BONUS)

    # add points for the team(s) that win each GW
    # determine top scoring players for each GW and add points to their teams ("Green Jersey")
    for gw in winners_by_gw:
        for team in winners_by_gw[gw][1]:
            team.add_points(GW_MAX_AVERAGE_BONUS)

        gw_points_by_player = {}
        for player in players:
            gw_points_by_player[player] = player.get_points_for_gw(gw + 1)
        sorted_gw_points_by_player = sorted(gw_points_by_player.items(), key=operator.itemgetter(1), reverse=True)
        for i in xrange(MAX_POSITION_FOR_AWARD):
            team = sorted_gw_points_by_player[i][0].get_team()
            team.add_points(POSITIONS_AWARDS[i + 1])

    for team in teams:
        print(team.name + ' : ' + str(team.get_points()))
