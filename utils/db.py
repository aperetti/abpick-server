from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.collection import Collection
from datetime import datetime
from typing import Union, List, TypedDict
from od_python import InlineResponse2009, InlineResponse20015, InlineResponse200


class AbilityPlayer(TypedDict):
    _id: int
    account_id: int
    last_run: int


class PlayerMatches(TypedDict):
    _id: int
    assists: int
    deaths: int
    duration: int
    game_mode: int
    hero_id: int
    kills: int
    lobby_type: int
    match_id: int
    player_slot: int
    radiant_win: bool
    skill: int
    start_time: int
    version: int


class Collections:
    ab_players = "ab_players"
    matches = "matches"
    match_details = "match_details"


def add_id(
        document: Union[List[InlineResponse2009], List[InlineResponse20015], InlineResponse2009, InlineResponse20015],
        key) -> Union[List[dict], dict]:
    if isinstance(document, list):
        return [{"_id": x.to_dict()[key], **(x.to_dict())} for x in document]
    else:
        document = document.to_dict()
        document["_id"] = document[key]
        return document


class Database:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.dota
        self.matches: Collection = self.db[Collections.matches]
        self.ab_players: Collection = self.db[Collections.ab_players]
        self.match_details: Collection = self.db[Collections.match_details]

    def get_player(self, account_id):
        player: AbilityPlayer = self.ab_players.find_one(account_id)
        return player

    def insert_player_matches(self, player_history: List[InlineResponse20015], player_id):
        """

        :param player_history: standard response from ODOTA player match history API
        :param player_id: steam ID of the player
        :return lowest_id
        """
        player_history: list = add_id(player_history, "match_id")
        for match in player_history:
            res = self.matches.update_one({"_id": match["match_id"]}, {"$set": match}, upsert=True)

            self.ab_players.update_one(
                {"_id": player_id},
                {
                    "$set": {"last_run": datetime.now().timestamp()}
                },
                upsert=True
            )

        return

    def insert_match_details(self, match: InlineResponse2009):
        """

        :param match:
        :return:
        """
        match = add_id(match, "match_id")
        try:
            res = self.match_details.insert_one(match)
            self.matches.update_one({"_id": match["_id"]}, {"$set": {"parsed": True}})
            for player in match["players"]:
                player_won = (player["radiant_win"] and player["player_slot"] < 5) or (not player["radiant_win"] and player["player_slot"] >= 5)
                good_skill = (match["skill"] or 0) >= 2
                if player["account_id"] is not None:
                    self.ab_players.update_one({"_id": player['account_id']},
                        {
                            "$max": {"last_run": 0},
                            "$set": {"rank": player["rank_tier"]},
                            "$inc": {
                                "win": 1 if player_won else 0,
                                "skill": 1 if good_skill else 0,
                                "played": 1,
                            }
                        },
                        upsert=True)
        except DuplicateKeyError:
            print(f"Already Parsed {match['match_id']}")


    def get_unparsed_matches(self) -> List[PlayerMatches]:
        return list(self.matches.find({"parsed": {"$ne": True}}, {"match_id": 1}))

    def update_player_ranks(self):
        for player in self.ab_players.find():
            match = self.match_details.find_one(
                {"players": {"$elemMatch": {"account_id": player["_id"]}}},
                { "players.$": 1}
                )
            rank = match["players"][0]["rank_tier"]
            self.ab_players.update_one({"_id": player["_id"]}, {"$set": {"rank": rank}})


if __name__ == "__main__":
    db = Database()
    db.update_player_ranks()