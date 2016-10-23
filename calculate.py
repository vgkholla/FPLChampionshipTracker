import dryscrape
import operator
import os

from bs4 import BeautifulSoup
from ConfigParser import SafeConfigParser

class Config(object):
    """Contains all the configuration and provides easy API access"""

    PLAYERS_SECTION = 'Players'
    TEAMS_SECTION = 'Teams'
    RULES_SECTION = 'Rules'
    REQUIRED_SECTIONS = [ PLAYERS_SECTION, TEAMS_SECTION, RULES_SECTION ]

    def __init__(self, configFile):
        self.config = SafeConfigParser()
        self.config.read(configFile)
        for required_section in self.REQUIRED_SECTIONS:
            if not self.config.has_section(required_section):
                raise Exception('Required section [' + required_section + '] does not exist')
        self.gw_positions_awards = [float(i) for i in self.config.get(self.RULES_SECTION, 'GwPositionsAwards').split(',')]
        self.hw_positions_awards = [float(i) for i in self.config.get(self.RULES_SECTION, 'HwPositionsAwards').split(',')]
        self.eos_positions_awards = [float(i) for i in self.config.get(self.RULES_SECTION, 'EosPositionsAwards').split(',')]


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

    def get_max_sum_player_count(self):
        return self.config.getint(self.RULES_SECTION, 'MaxSumPlayerCount')

    def get_max_position_for_award(self):
        return self.config.getint(self.RULES_SECTION, 'MaxPositionForAward')

    def get_gw_max_average_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'GwMaxAverageBonus')

    def get_gw_max_sum_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'GwMaxSumBonus')

    def get_gw_positions_awards(self):
        return self.gw_positions_awards

    def get_hw_mark(self):
        return self.config.getint(self.RULES_SECTION, 'HwMark')

    def get_hw_max_average_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'HwMaxAverageBonus')

    def get_hw_max_sum_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'HwMaxSumBonus')

    def get_hw_positions_awards(self):
        return self.hw_positions_awards

    def get_eos_mark(self):
        return self.config.getint(self.RULES_SECTION, 'Eos')

    def get_eos_max_average_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'EosAverageBonus')

    def get_eos_max_sum_bonus(self):
        return self.config.getfloat(self.RULES_SECTION, 'EosSumBonus')

    def get_eos_positions_awards(self):
        return self.eos_positions_awards

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
        self.points = 0.0
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
                    self.team_averages_by_gw[i] += player_points[i]
        total = 0
        for i in xrange(len(self.team_averages_by_gw)):
            self.team_averages_by_gw[i] = float(self.team_averages_by_gw[i]) / float(len(self.players))
            total += self.team_averages_by_gw[i]
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

    def get_team_averages_by_gw(self):
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

    def get_players_sorted_by_points_at_gw(self, gameweek):
        if gameweek <= 0 or gameweek > len(self.team_averages_by_gw):
            raise Exception('Data for GW-' + gameweek + ' does not exist')
        points = {}
        for player in self.players.items():
            points[player] = 0
            for i in xrange(gameweek):
                points[player] += player[1].get_points_for_gw(i + 1)
        return sorted(points.items(), key=operator.itemgetter(1), reverse=True) 

    def add_points(self, points):
        self.points += float(points)
        return self.points

    def get_points(self):
        return self.points

class MessageSender(object):
    """Sends provided messages to configured endpoint"""
    
    def __init__(self):
        pass

    def send_message(self, message):
        print(message)

def add_pos_points(config, players_sorted_by_points, position_awards):
    players_at_pos = []
    curr_base = 0
    count_for_pos = 0
    curr_qual = players_sorted_by_points[0][1]
    i = 0
    while curr_base < config.get_max_position_for_award():
        if i < len(players_sorted_by_points):
            points = players_sorted_by_points[i][1]
        if i >= len(players_sorted_by_points) or points != curr_qual:
            points_for_pos = 0
            for j in xrange(count_for_pos):
                if curr_base + j >= config.get_max_position_for_award():
                    break
                points_for_pos += position_awards[curr_base + j]
            points_for_pos = float(points_for_pos) / float(count_for_pos)
            for player in players_at_pos:
                team = player.get_team()
                team.add_points(points_for_pos)

            players_at_pos = []
            curr_base += count_for_pos
            count_for_pos = 0
            curr_qual = points
        count_for_pos += 1
        players_at_pos.append(players_sorted_by_points[i][0])
        i += 1

def add_stage_bonus(config, teams, gameweek, team_averages_at_gameweek, max_avg_bonus, max_sum_bonus):
    sorted_averages = sorted(team_averages_at_gameweek.items(), key=operator.itemgetter(1), reverse=True)
    highest_average = sorted_averages[0][1]
    i = 0
    while i < len(sorted_averages):
        if sorted_averages[i][1] == highest_average:
            team = sorted_averages[i][0]
            team.add_points(max_avg_bonus)
        else:
            break
        i +=1
    max_top_sum = 0
    max_top_sum_teams = []
    for team in teams:
        players_sorted_by_points = team.get_players_sorted_by_points_at_gw(gameweek)
        top_players_sum = 0
        for position in xrange(config.get_max_sum_player_count()):
            top_players_sum += players_sorted_by_points[position][1]
        if top_players_sum == max_top_sum:
            max_top_sum_teams.append[team]
        elif top_players_sum > max_top_sum:
            max_top_sum = top_players_sum
            max_top_sum_teams = [team]
    for team in max_top_sum_teams:
        team.add_points(max_sum_bonus)

if __name__ == '__main__':
    message_sender = MessageSender()
    dir_name = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_name, 'game.config')
    config = Config(config_path)

    teams = []
    players = []
    for team in config.get_teams():
        team_obj = Team(team, config)
        if len(team_obj.get_players()) < config.get_max_sum_player_count():
            raise Exception(team.name + ' does not have enough players to calculate max top invidual players sum - ' + str(config.get_max_sum_player_count()))
        for player in team_obj.get_players().items():
            players.append(player[1])
        teams.append(team_obj)

    winners_by_gw = {}
    max_top_sum_by_gw = {}

    hw_averages = {}
    eos_averages = {}

    # determine team(s) that wins in each game week
    # determine averages at halfway and EOS
    # determine the team(s) that has the max sum for config.get_max_sum_player_count() members
    for team in teams:
        averages_by_gw = team.get_team_averages_by_gw()
        curr_average = 0
        for i in xrange(len(averages_by_gw)):
            curr_average += averages_by_gw[i]
            if i == config.get_hw_mark() - 1 :
                hw_averages[team] = curr_average
            elif i == config.get_eos_mark() - 1 : 
                eos_averages[team] = curr_average

            if i not in winners_by_gw or winners_by_gw[i][0] < averages_by_gw[i]:
                winners_by_gw[i] = (averages_by_gw[i], [team])
            elif winners_by_gw[i][0] == averages_by_gw[i]:
                winners_by_gw[i][1].append(team)
            
            players_sorted_by_points = team.get_players_sorted_by_points_for_gw(i + 1);
            top_players_sum = 0
            for position in xrange(config.get_max_sum_player_count()):
                top_players_sum += players_sorted_by_points[position][1]
            if i not in max_top_sum_by_gw or max_top_sum_by_gw[i][0] < top_players_sum:
                max_top_sum_by_gw[i] = (top_players_sum, [team])
            elif max_top_sum_by_gw[i][0] == top_players_sum:
                max_top_sum_by_gw[i][1].append(team)


    # add points for the team(s) that win each GW
    # add points to the team(s) that have the max sum for config.get_max_sum_player_count() members every GW
    for gw in winners_by_gw:
        for team in winners_by_gw[gw][1]:
            team.add_points(config.get_gw_max_average_bonus())

        for team in max_top_sum_by_gw[gw][1]:
            team.add_points(config.get_gw_max_sum_bonus())

    gw_count = len(winners_by_gw)

    # determine top scoring players for each GW and add points to their teams ("Green Jersey")
    # determine top scoring players at halfway and end of season ("Yellow Jersey")
    points_till_now_by_player = {}
    for gw in xrange(gw_count):
        gw_points_by_player = {}
        for player in players:
            gw_points_by_player[player] = player.get_points_for_gw(gw + 1)
            if player not in points_till_now_by_player:
                points_till_now_by_player[player] = 0
            points_till_now_by_player[player] += gw_points_by_player[player]
        gw_points_by_player_sorted = sorted(gw_points_by_player.items(), key=operator.itemgetter(1), reverse=True)
        points_till_now_by_player_sorted = sorted(points_till_now_by_player.items(), key=operator.itemgetter(1), reverse=True)

        add_pos_points(config, gw_points_by_player_sorted, config.get_gw_positions_awards())
        if gw == config.get_hw_mark() - 1 :
            add_pos_points(config, points_till_now_by_player_sorted, config.get_hw_positions_awards())
        elif gw == config.get_eos_mark() - 1 : 
            add_pos_points(config, points_till_now_by_player_sorted, config.get_eos_positions_awards())

    # halfway bonuses
    # max sum and top two players max sum
    if gw_count >= config.get_hw_mark() - 1:
        add_stage_bonus(config, teams, config.get_hw_mark(), hw_averages, config.get_hw_max_average_bonus(), config.get_hw_max_sum_bonus())

    # end of season bonuses
    # max sum and top two players max sum
    if gw_count >= config.get_eos_mark() - 1:
        add_stage_bonus(config, teams, config.get_eos_mark(), eos_averages, config.get_eos_max_average_bonus(), config.get_eos_max_sum_bonus())

    message = 'FPLBot:\n'
    for team in teams:
        message = message + team.name + ' - ' + str(team.get_points()) + "\n"
    
    message_sender.send_message(message)
