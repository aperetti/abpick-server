from xgboost import XGBRegressor
import numpy as np
from pymongo import MongoClient
from utils import load_list_ad_abilitity_ids
labels =["y_damage", "y_gold", "y_kills", "y_deaths", "y_win"]

def load_model(model_name):
    model = XGBRegressor()
    model.load_model(f"resources/{model_name}.json")
    return model

class Predictor:
    def __init__(self):
        self.models = {x: load_model(x) for x in labels}
        self.ab = load_list_ad_abilitity_ids()
        self.ab_lu = {v: k for k, v in enumerate(self.ab)}
        self.ab_pos = {k: v for k, v in enumerate(self.ab)}

    def predict(self, picked_skills, available_skills):
        pos = [self.ab_lu[x] for x in picked_skills]
        avb_pos = [self.ab_lu[x] for x in available_skills]
        x = np.zeros(len(self.ab))
        x[pos] = 1
        X = np.zeros((len(available_skills), len(self.ab))) + x
        idx = np.expand_dims(avb_pos, axis=1)
        val = np.expand_dims(np.ones((len(avb_pos))), axis=1)
        np.put_along_axis(X, idx, val, axis=1)
        ys = { label: self.models[label].predict(X) for label in labels }
        predictions = {}
        for i, skill in enumerate(available_skills):
            predictions[skill] = { label.split("_")[1]: float(ys[label][i]) for label in labels }

        return predictions


class Trainer:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.get_database("dota")
        self.matches: Collection = self.db.match_details

    def get_draft_training_set(self):

        cursor = self.matches.find(
                    {
                        "duration": {"$gt": 900},
                        "start_time": {"$gt": time.time() - 60*60*24*self.days}
                    }
        )
        ab = load_list_ad_abilitity_ids()
        ab_lu = {v: k for k, v in enumerate(ab)}
        X_skills = []
        y_damage = []
        y_win = []
        y_kills = []
        y_deaths = []
        y_gold = []


        for i, match in enumerate(cursor):
            duration = match["duration"] / 60

            for pos, player in enumerate(match["players"]):
                try:
                    gold = player["gold_per_min"]
                    damage = player["hero_damage"] / duration
                    kills = player["kills"] / duration
                    deaths = player["deaths"] / duration
                    win = player["win"]
                    player_abilities = set(player["ability_upgrades_arr"])
                    x_skills=np.zeros((len(ab)))
                    x_skills[[ab_lu[s] for s in player_abilities if s in ab_lu]]=1

                    y_gold.append(gold)
                    y_damage.append(damage)
                    y_kills.append(kills)
                    y_deaths.append(deaths)
                    y_win.append(win)
                    X_skills.append(x_skills)

                except (KeyError, TypeError) as e:
                    print(f"{i}-{match['_id']}-{e}")

        training_set = dict(
        y_gold = (y_gold),
        y_damage = (y_damage),
        y_kills = (y_kills),
        y_deaths = (y_deaths),
        y_win = (y_win),
        X_skills = (X_skills)
        )

        pickle.dump( training_set, open('resources/skill_training.pkl', 'wb'))
        return training_set

    def load_training_set(self):
        return pickle.load(open('resources/skill_training.pkl', 'rb'))

    def prepare_data(self, training_set, label, split=.9):
        X = np.asarray(training_set["X_skills"])

        y = np.asarray(training_set[label])

        split_idx = int(X.shape[0]*.9)

        train = Dataset(X[:split_idx, :], y[:split_idx])
        test = Dataset(X[split_idx:, :], y[split_idx:])
        return train, test

    def generate_models(self):
        params = dict(n_estimators=1000, max_depth=7, eta=0.1, subsample=0.7, colsample_bytree=0.8, early_stopping_rounds=20)
        training_set = self.load_training_set()
        for label in labels:
            train, test = self.prepare_data(training_set, label)
            model = XGBRegressor(**params)
            model.fit(train.X, train.y, eval_set=[(test.X, test.y)])
            model.save_model(f"resources/{label}.json")


if __name__ == "__main__":
    pass