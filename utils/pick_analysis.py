from pymongo.mongo_client import MongoClient
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor
from typing import Union, Tuple
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import time
from constant_loaders import load_list_ad_abilitity_ids
from xgboost import DMatrix, train, XGBRegressor
import pickle
from dataclasses import dataclass
import json

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
        self.days = 60
        self.ability_id = None
        self.pick_data = None

    def get_distinct_abilities(self, period: Union[Tuple[int, int], None] = None):
        if period is None:
            res = self.matches.distinct("ability_draft.skills")
        else:
            res = self.matches.distinct("ability_draft.skills", {"start_time": {"$gt": period[0], "$lt": period[1]}})
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

        arr = np.hstack([arr, (arr[:, 1] % 2 == (arr[:, 0] + 1) % 2)[..., None]])
        df = pd.DataFrame(arr, columns=['radiant_win', 'pick', 'win'])
        df.loc[df['pick'] == -1, 'pick'] = 40

        return df

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
            pick_rate=df.loc[df['pick'].between(0, 39), 'pick'].count() / picks,
            pick_rate_rounds=[df.loc[df['pick'].between(x*10, x*10+9), 'pick'].count() / picks for x in range(4)]
        )

    def get_pick_win_rates(self):
        df = self.pick_data
        return dict(
            win_rate=df['win'].mean(),
            win_rate_rounds=[df.loc[df['pick'].between(x * 10, x * 10 + 9), 'win'].mean() for x in range(4)]
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


if __name__ == '__main__':
    # df_main = PickAnalysis().get_draft_training_set()
    df_main = PickAnalysis().generate_models()

