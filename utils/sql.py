from sqlite3 import dbapi2
import sys
from typing import List

db = dbapi2.connect("../database.db")


def init_database():
    """
    Initializes the database
    """
    db.executescript(open('sql/CREATE_TABLES.sql', 'r').read())


def insert_player_matches(player_history: List[dict], player_id: int):
    """

    :param player_history: standard response from ODOTA player match history API
    :param player_id: steam ID of the player
    :param game_mode_filter: an option parameter which filters out games not matching the parameter,
        no filters are applied if parameter is None
    :return: lowest match id
    """

    low_match_id = sys.maxsize
    for match in player_history:
        db.execute("INSERT INTO matches(match_id, start_time, game_mode, leaver_status, ) VALUES "
                   "(:match_id, :start_time, :game_mode);",
                   parameters={"match_id": match['match_id'],
                               "start_time": match['start_time'],
                               "game_mode": match['game_mode']})

        db.execute("UPDATE ab_players "
                   "SET last_played = :start_time "
                   "WHERE player_id = :played_id "
                   "    AND last_played < :start_time; ab_players",
                   parameters={"start_time": match['start_time'],
                               "player_id": player_id})

        low_match_id = min(match['match_id'], low_match_id)

    return low_match_id

def insert_match_details(match_details):
    """

    :param match_details: standard response from ODOTA matchd details
    :return:
    """