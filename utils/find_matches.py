import od_python
from od_python import InlineResponse20015, InlineResponse2009, rest
from typing import List
from db import Database, AbilityPlayer
from datetime import timedelta, datetime
from os import environ
from tqdm.auto import tqdm

api_key = environ.get('API_KEY')
print(api_key)
client = od_python.ApiClient(header_name="Authorization", header_value=f"Bearer {api_key}")


class FindMatches:
    def __init__(self):
        self.player_client = od_python.PlayersApi(api_client=client)
        self.match_client = od_python.MatchesApi(api_client=client)
        self.db = Database()
        pass

    def find_new_matches(self, account_id, age_limit: timedelta = timedelta(weeks=8), max_queries=100):
        player = self.db.get_player(account_id)
        for i in range(max_queries):
            try:
                matches: List[InlineResponse20015] = self.player_client.players_account_id_matches_get(account_id,
                                                                                                    game_mode=18,
                                                                                                    significant=0,
                                                                                                    offset=i * 50)
            except rest.ApiException:
                continue

            matches = [match for match in matches if
                       match.start_time + age_limit.total_seconds() > datetime.now().timestamp()]
            if matches is None or len(matches) == 0:
                break
            self.db.insert_player_matches(matches, account_id)
            oldest_match = min(matches, key=lambda x: x.match_id)
            oldest_match_datetime = datetime.fromtimestamp(oldest_match.start_time)

            if oldest_match_datetime + age_limit < datetime.now():
                break

            if player['last_run'] > oldest_match.start_time:
                break

    def get_ab_players(self) -> List[AbilityPlayer]:
        players: List[AbilityPlayer] = list(self.db.ab_players.find().sort([("last_run", -1)]))
        players = [x for x in players if datetime.fromtimestamp(x['last_run']) + timedelta(weeks=2) < datetime.now()]
        return players

    def parse_matches(self, bar_position=0):
        matches = self.db.get_unparsed_matches()
        match_count = 0
        for match in tqdm(matches, desc="Parsing Matches", position=bar_position):
            match_count += 1
            match_detail: InlineResponse2009 = self.match_client.matches_match_id_get(match_id=match['match_id'])
            self.db.insert_match_details(match_detail)
        return match_count

    def prime_players(self):
        self.db.get


if __name__ == "__main__":

    search = FindMatches()

    players = search.get_ab_players()
    total_parsed = 0
    for player in tqdm(players, "Finding New Matches from AB Players", position=0):
        search.find_new_matches(player['_id'])
        total_parsed += search.parse_matches(bar_position=1)
        if total_parsed > 50000:
            break
