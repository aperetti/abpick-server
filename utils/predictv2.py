from dataclasses import dataclass
from re import X
from tqdm import tqdm
from xgboost import XGBRegressor
import numpy as np
from pymongo import MongoClient
from pymongo.collection import Collection
from constant_loaders import load_list_ad_abilitity_ids
import pickle
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import Lasso
import time
from itertools import combinations, product
import json
# from tensorflow import one_hot, keras
from typing import List


@dataclass
class AbilityTrainingDataset:
    y_gold: List[float]
    y_damage: List[float]
    y_kills: List[float]
    y_deaths: List[float]
    y_win: List[float]
    y_assits: List[float]
    X_team: np.ndarray
    y_team_win: List[int]
    X_skills: np.ndarray


labels = ["y_damage", "y_gold", "y_kills", "y_deaths", "y_win"]


def load_model(model_name):
    model = XGBRegressor()
    model.load_model(f"resources/{model_name}.json")
    return model


@dataclass
class Dataset:
    X: np.array
    y: np.array


class SkillTrainer:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.get_database("dota")
        self.matches: Collection = self.db.match_details
        self.combos: Collection = self.db.combos
        self.days = 60

    def update_ability_one_hot(self):
        abilities = self.db.abilities.find({}).sort("one_hot", -1)
        max_id = 0
        for ab in abilities:
            t_oh = ab.get("one_hot")
            if t_oh is None:
                self.db.abilities.update_one(
                    {"_id": ab["_id"]}, {"$set": {"one_hot": max_id}})
                max_id += 1
            else:
                max_id = max(max_id, t_oh+1)

    def get_ability_one_hot_dict(self):
        abs = self.db.abilities.find({"one_hot": {"$exists": True}})
        ab_dict = {}
        max_id = 0
        for ab in abs:
            ab_dict[ab["_id"]] = ab["one_hot"]
            max_id = max(max_id, ab["one_hot"])
        return ab_dict, max_id+1

    def get_draft_training_set(self):

        cursor = self.matches.find(
            {
                "duration": {"$gt": 900},
                "start_time": {"$gt": time.time() - 60*60*24*self.days}
            }
        )
        ab_dict, max_features = self.get_ability_one_hot_dict()
        # ab = [str(x) for x in load_list_ad_abilitity_ids()]
        # qry = self.combos.find({}, {"_id": 1})
        # for res in qry:
        #     ab.append(f"{res['_id']['skill1']}|{res['_id']['skill2']}")
        encoder = OneHotEncoder()
        X_skills = []
        y_damage = []
        y_win = []
        y_kills = []
        y_deaths = []
        y_gold = []
        y_assists = []
        X_team = []
        y_team_win = []

        for i, match in tqdm(enumerate(cursor)):
            duration = match["duration"] / 60
            team_r = np.zeros(max_features)
            team_d = np.zeros(max_features)

            for i, player in enumerate(match["players"]):
                try:
                    gold = player["gold_per_min"]
                    damage = player["hero_damage"] / duration
                    kills = player["kills"] / duration
                    deaths = player["deaths"] / duration
                    assists = player["assists"] / duration
                    win = player["win"]
                    x_skills = np.zeros(max_features)
                    x_skills[[ab_dict[s] for s in set(
                        player["ability_upgrades_arr"])if s in ab_dict]] = 1
                    # add combos
                    # x_skills.extend(
                    #     [f"{x[0]}|{x[1]}" for x in combinations(x_skills, 2)])
                    if i % 2 == 0:
                        team_r += x_skills
                    else:
                        team_d += x_skills
                    y_gold.append(gold)
                    y_damage.append(damage)
                    y_kills.append(kills)
                    y_deaths.append(deaths)
                    y_win.append(win)
                    y_assists.append(assists)
                    X_skills.append(x_skills)
                except (KeyError, TypeError) as e:
                    pass

            if len(team_r) > 0:
                X_team.append(team_r)
                X_team.append(team_d)
                y_team_win.append(1 if match["radiant_win"] else 0)
                y_team_win.append(1 if not match["radiant_win"] else 0)

        training_set = AbilityTrainingDataset(
            y_gold=(y_gold),
            y_damage=(y_damage),
            y_kills=(y_kills),
            y_deaths=(y_deaths),
            y_win=(y_win),
            y_assits=(y_assists),
            X_team=np.asarray(X_team),
            y_team_win=(y_team_win),
            X_skills=np.asarray(X_skills)
        )

        pickle.dump(training_set, open(
            'resources/skill_training_v2.pkl', 'wb'))
        return training_set

    def load_training_set(self) -> AbilityTrainingDataset:
        return pickle.load(open('resources/skill_training_v2.pkl', 'rb'))

    def prepare_data(self, training_set, label, split=.9):
        X = np.asarray(training_set["X_skills"])

        y = np.asarray(training_set[label])

        split_idx = int(X.shape[0]*split)

        train = Dataset(X[:split_idx, :], y[:split_idx])
        test = Dataset(X[split_idx:, :], y[split_idx:])
        return train, test

    def generate_models(self):
        params = dict(n_estimators=1000, max_depth=7, eta=0.1,
                      subsample=0.7, colsample_bytree=0.8, early_stopping_rounds=20)
        training_set = self.load_training_set()
        for label in labels:
            train, test = self.prepare_data(training_set, label)
            model = XGBRegressor(**params)
            model.fit(train.X, train.y, eval_set=[(test.X, test.y)])
            model.save_model(f"resources/{label}.json")

    def normalize_X(self, X):
        length = max(map(len, X))
        return np.array([xi+[None]*(length-len(xi)) for xi in X])

    def prepare_team_data(self, training_set: AbilityTrainingDataset, split=.9):
        X = np.asarray(training_set.X_team)
        X = np.reshape(X, (int(X.shape[0]/2), int(X.shape[1]*2)))
        y = training_set.y_team_win[::2]

        split_idx = int(X.shape[0]*split)

        train = Dataset(X[:split_idx, :], y[:split_idx])
        test = Dataset(X[split_idx:, :], y[split_idx:])

        return train, test

    def generate_regression_team(self):
        l = Lasso()
        training_set = self.load_training_set()
        train, test, encoder = self.prepare_team_data(training_set, .999)
        l.fit(train.X, train.y)
        json.dump(l.get_params(), open(f"resources/team_predict.json", 'w+'))
        json.dump(encoder.get_params(), open('resoures/encoder.json', 'w+'))

    def generate_team_model(self):
        n_estimators = [50, 100, 500]
        max_depth = [8, 12, 20]
        eta = [0.01, 0.05]
        hypers = product(n_estimators, max_depth, eta)
        training_set = self.load_training_set()
        train, test = self.prepare_team_data(training_set)
        models = []
        for n_est, max_d, et in hypers:
            print(n_est, max_d, et)
            params = dict(n_estimators=n_est, max_depth=max_d, eta=et, objective='binary:logistic',
                          subsample=1, colsample_bytree=1, early_stopping_rounds=20)
            model = XGBRegressor(**params)
            model.fit(train.X, train.y, eval_set=[(test.X, test.y)])
            models.append({
                "params": (n_est, max_d, et),
                "model": model,
            })


        best_models = sorted(models, key=lambda x: x['model'].best_score)
        for bm in best_models:
            print(bm["params"], bm["model"].best_score)

    def generate_player_model(self):
        ds = self.load_training_set()
        pass


class SkillPredictor:
    def __init__(self):
        self.models = {x: load_model(x) for x in labels}
        self.models['team'] = load_model('team_predict')
        self.encoder = OneHotEncoder().set_params(json.load('resources/encoder.json'))
        self.ab_lu = {v: k for k, v in enumerate(self.ab)}
        self.ab_pos = {k: v for k, v in enumerate(self.ab)}

        X = self.encoder.transform(skills)
        y = self.models['team'].predict(X)
        return y

    def predict(self, picked_skills, available_skills):
        pos = [self.ab_lu[x] for x in picked_skills]
        avb_pos = [self.ab_lu[x] for x in available_skills]
        x = np.zeros(len(self.ab))
        x[pos] = 1
        X = np.zeros((len(available_skills), len(self.ab))) + x
        idx = np.expand_dims(avb_pos, axis=1)
        val = np.expand_dims(np.ones((len(avb_pos))), axis=1)
        np.put_along_axis(X, idx, val, axis=1)
        ys = {label: self.models[label].predict(X) for label in labels}
        predictions = {}
        for i, skill in enumerate(available_skills):
            predictions[skill] = {label.split("_")[1]: float(
                ys[label][i]) for label in labels}

        return predictions


if __name__ == "__main__":
    t = SkillTrainer()

    # t.update_ability_one_hot()
    # t.get_draft_training_set()
    # t.generate_regression_team()
    # t.generate_player_model()
    t.generate_team_model()
    pass
