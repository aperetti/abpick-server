import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.errors import WriteError
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor
from typing import Union, Tuple
import numpy as np
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import time
from dataclasses import dataclass
from itertools import combinations
from collections import defaultdict, Counter
import json
from requests import delete
from tqdm import tqdm


class NoSkillDataException(Exception):
    pass


@dataclass
class Dataset:
    X: np.array
    y: np.array


def updatePlayerStats():
    client = MongoClient()
    db = client.get_database("dota")
    matches: Collection = db.match_details
    players: Collection = db.players

    {"$and": [{"skill": {"$ne": null}}, {"skill": {"$ne": 1}}]}


class PickAnalysis:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.get_database("dota")
        self.matches: Collection = self.db.match_details
        self.abilities: Collection = self.db.get_collection("abilities")
        self.ab_abilities: Collection = self.db.get_collection("ab_abilities")
        self.days = 90
        self.ability_id = None
        self.pick_data = None

    def get_distinct_abilities(self, period: Union[Tuple[int, int], None] = None):
        if period is None:
            res = self.matches.distinct("ability_draft.skills")
        else:
            res = self.matches.distinct("ability_draft.skills", {"start_time": {
                                        "$gt": period[0], "$lt": period[1]}})
        return res

    def save_ab_abilities(self):
        abilities = self.get_distinct_abilities()
        self.ab_abilities.update_one(
            {"_id": "latest"},
            {"$set":
                {
                    "abilities": abilities,
                    "last_run": int(datetime.utcnow().timestamp())
                }
             },
            upsert=True
        )

    def __load_ability_picks__(self) -> pd.DataFrame:
        cursor: CommandCursor = self.matches.aggregate(
            [
                {"$match":
                    {
                        "ability_draft.skills": self.ability_id,
                        "duration": {"$gt": 900},
                        "start_time": {"$gt": time.time() - 60*60*24*self.days}
                    }
                 },
                {
                    "$project": {
                        "position": {"$indexOfArray": ["$ability_draft.drafts", self.ability_id]},
                        "radiant_win": 1
                    }
                }
            ])

        arr = np.asarray([[x['radiant_win'], x['position']] for x in cursor])
        if arr.size == 0:
            raise NoSkillDataException

        arr = np.hstack(
            [arr, (arr[:, 1] % 2 == (arr[:, 0] + 1) % 2)[..., None]])
        df = pd.DataFrame(arr, columns=['radiant_win', 'pick', 'win'])
        df.loc[df['pick'] == -1, 'pick'] = 40

        return df

    def __load_ability_picks__(self) -> pd.DataFrame:
        cursor: CommandCursor = self.matches.aggregate(
            [
                {"$match":
                    {
                        "ability_draft.skills": self.ability_id,
                        "duration": {"$gt": 900},
                        "start_time": {"$gt": time.time() - 60*60*24*self.days}
                    }
                 },
                {
                    "$project": {
                        "position": {"$indexOfArray": ["$ability_draft.drafts", self.ability_id]},
                        "radiant_win": 1
                    }
                }
            ])

        arr = np.asarray([[x['radiant_win'], x['position']] for x in cursor])
        if arr.size == 0:
            raise NoSkillDataException

        arr = np.hstack(
            [arr, (arr[:, 1] % 2 == (arr[:, 0] + 1) % 2)[..., None]])
        df = pd.DataFrame(arr, columns=['radiant_win', 'pick', 'win'])
        df.loc[df['pick'] == -1, 'pick'] = 40

        return df

    def combo_picks(self):
        # combo_dict = defaultdict(Counter)
        # wins, played, gold, damage, kills, deaths, assists, xp, tower
        combo_dict = defaultdict(lambda: np.zeros(9).astype(np.float64))
        single_dict = defaultdict(lambda: np.zeros(9).astype(np.float64))
        combos = self.db.get_collection('combos')
        cursor: CommandCursor = self.matches.find(
            {
                "duration": {"$gt": 900},
                "start_time": {"$gt": time.time() - 60*60*24*self.days}
            },
            {
                "players.ability_upgrades_arr": 1,
                "players.gold_per_min": 1,
                "players.hero_damage": 1,
                "players.kills": 1,
                "players.deaths": 1,
                "players.assists": 1,
                "players.xp_per_min": 1,
                "players.tower_damage": 1,
                "duration": 1,
                "radiant_win": 1
            }
        )

        for match in tqdm(cursor):
            mmin = match['duration'] / 60
            for i, player in enumerate(match['players']):
                win = 1 if (i % 2 == 0 and match['radiant_win']) or (
                    i % 2 == 1 and not match['radiant_win']) else 0
                skills = np.unique(player['ability_upgrades_arr'])

                # wins, played, gold, damage, kills, deaths, assists, xp, tower
                new_stats = [win, 1, player['gold_per_min'], player['hero_damage'] / mmin,
                             player['kills'] / mmin, player['deaths'] /
                             mmin, player['assists'] / mmin,
                             player['xp_per_min'], player['tower_damage'] / mmin]
                for skill in skills:
                    single_dict[skill] += new_stats
                for combo in combinations(np.unique(player['ability_upgrades_arr']), 2):
                    combo_dict[combo] += new_stats

        def get_synergy(skill1, skill2):
            skill1_win = single_dict[skill1][0] * 1.0 / single_dict[skill1][1]
            skill2_win = single_dict[skill2][0] * 1.0 / single_dict[skill2][1]
            return (skill1_win + skill2_win)/2

        combos.delete_many({})
        combo_docs = [
            {
                "_id": {"skill1": int(key[0]), "skill2": int(key[1])},
                "avg_win_pct": get_synergy(key[0], key[1]),
                "win_pct": vals[0] / vals[1],
                "gold": vals[2] / vals[1],
                "damage": vals[3] / vals[1],
                "kills": vals[4] / vals[1],
                "deaths": vals[5] / vals[1],
                "assists": vals[6] / vals[1],
                "xp": vals[7] / vals[1],
                "tower": vals[8] / vals[1],
                "matches": vals[1]
            } for key, vals in combo_dict.items() if vals[1] > 50]
        combos.insert_many(combo_docs)
        for skill_id, vals in single_dict.items():
            try:
                if skill_id is None:
                    continue
                self.abilities.update_one(
                    {"_id": int(skill_id)},
                    {"$set":
                     {
                         "win_rate": vals[0] / vals[1],
                         "gold": vals[2] / vals[1],
                         "damage": vals[3] / vals[1],
                         "kills": vals[4] / vals[1],
                         "deaths": vals[5] / vals[1],
                         "assists": vals[6] / vals[1],
                         "xp": vals[7] / vals[1],
                         "tower": vals[8] / vals[1],
                     }
                     }
                )
            except WriteError as e:
                print(f"Failed to write {skill_id}")

        pass

    def save_pick_analytics(self):
        self.abilities.update_one(
            {"_id": self.ability_id},
            {"$set":
                dict(
                    survival=list(self.get_pick_survival()),
                    **self.get_pick_win_rates(),
                    **self.get_pick_summary(),
                    **self.get_pick_rates()
                )
             },
            upsert=True
        )

    def get_pick_rates(self):
        df = self.pick_data
        picks = self.pick_data['pick'].count() * 1.0
        return dict(
            pick_rate=df.loc[df['pick'].between(
                0, 39), 'pick'].count() / picks,
            pick_rate_rounds=[df.loc[df['pick'].between(
                x*10, x*10+9), 'pick'].count() / picks for x in range(4)]
        )

    def get_pick_win_rates(self):
        df = self.pick_data
        return dict(
            win_rate_rounds=[df.loc[df['pick'].between(
                x * 10, x * 10 + 9), 'win'].mean() for x in range(4)]
        )

    def get_pick_summary(self):
        return self.pick_data['pick'].describe().to_dict()

    def get_pick_median(self):
        return self.pick_data['pick'].median()

    def get_pick_survival(self):
        data = self.pick_data
        df = (data
              .groupby('pick')
              .count()
              .sort_index()
              .reindex(pd.Index(range(data['pick'].min(), data['pick'].max() + 1)), fill_value=0)
              .iloc[:, [0]]
              .rename(columns={data.columns[0]: 'count'})
              )
        df['survival'] = ((1 - df['count'] / (df['count'].sum() - df['count'].shift(1).cumsum()))
                          .cumprod())

        df = df.reindex(range(40))

        df = df.where(df.ffill().notna(), 1)

        df = df.where(df.bfill().notna(), 0)

        return df['survival'].values

    def set_pick_id(self, ability_id):
        self.ability_id = ability_id
        self.pick_data = self.__load_ability_picks__()
        return self

    def hero_stats(self):
        cursor: CommandCursor = self.matches.find(
            {
                "duration": {"$gt": 900},
                "start_time": {"$gt": time.time() - 60*60*24*self.days}
            },
            {
                "players.ability_upgrades_arr": 1,
                "players.hero_id": 1,
                "players.gold_per_min": 1,
                "players.hero_damage": 1,
                "players.kills": 1,
                "players.deaths": 1,
                "players.assists": 1,
                "players.xp_per_min": 1,
                "players.tower_damage": 1,
                "duration": 1,
                "players.is_radiant": 1,
                "radiant_win": 1
            }
        )

        heros_coll = self.db.get_collection("heros")
        heros_coll.delete_many({})
        hero_skill = defaultdict(lambda: defaultdict(lambda: np.zeros(2, np.int64)))
        hero_stats = defaultdict(lambda: np.zeros(2, np.int64))
        for match in tqdm(cursor):
            for player in match["players"]:
                hero_id = player["hero_id"]
                win = 0 if (player["is_radiant"] ^ match["radiant_win"]) else 1
                hero_stats[hero_id] += [win, 1]

                for skill in np.unique(player['ability_upgrades_arr']):
                    hero_skill[hero_id][skill] += [win, 1]

        for hero_id, skills in tqdm(hero_skill.items()):
            h_stat = hero_stats[hero_id]
            hero_dict = {
                "_id": hero_id,
                "win_rate": float(h_stat[0] * 1.0 / h_stat[1])
            }

            hero_skills = []
            for skill_id, stats in skills.items():
                win_pct = float(stats[0] * 1.0 / (stats[1]))
                if stats[1] > 15 and win_pct - .5/np.sqrt(stats[1]) > .5:
                    hero_skills.append({
                        "id": int(skill_id),
                        "matches": int(stats[1]),
                        "win_rate": float(stats[0] * 1.0 / stats[1])
                    })
            hero_dict["skills"] = hero_skills
            heros_coll.insert_one(hero_dict)





if __name__ == '__main__':
    # df_main = PickAnalysis().combo_picks()
    df_main = PickAnalysis().hero_stats()
