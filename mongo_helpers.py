from pymongo import MongoClient
from pymongo.results import InsertOneResult
from datetime import datetime
from bson.objectid import ObjectId
from itertools import product

client = MongoClient()
db = client.get_database("dota")
room_collection = db.get_collection("rooms")

def getBestCombos(picked_skills, available_skills):
    combos = product(picked_skills, available_skills)
    search = []
    for x in combos:
        if x[0] > x[1]:
            search.append({"_id": {"skill1": x[1], "skill2": x[0]}})
        else:
            search.append({"_id": {"skill1": x[0], "skill2": x[1]}})
    curs = db.get_collection("combos").find({"$or": search})
    res = []
    for combo in curs:
        if combo["_id"]["skill1"] in picked_skills:
            skill = combo["_id"]["skill2"]
            picked = combo["_id"]["skill1"]
        else :
            skill = combo["_id"]["skill1"]
            picked = combo["_id"]["skill2"]

        res.append({"skill": skill, "picked": picked, "avg_win_pct": combo["avg_win_pct"], "win_pct": combo["win_pct"]})

    return res


def trim_state(state):
    return {k: v for k, v in state.items() if k in ["skills", "picks", "stateId", "room", "lastUpdate", "roomCount"]}


def get_active_room(room):
    result = room_collection.find_one({"lastUpdate": {"$gt": datetime.utcnow().timestamp() - 60 * 60}, "room": room})
    if result is not None:
        result["_id"] = str(result["_id"])
    return result


def update_room(id_string, state):
    state["lastUpdate"] = datetime.utcnow().timestamp()
    status = room_collection.update_one({"_id": ObjectId(id_string)}, {"$set": trim_state(state)})
    return status


def create_room(state):
    state["lastUpdate"] = datetime.utcnow().timestamp()
    res: InsertOneResult = room_collection.insert_one(trim_state(state))
    return str(res.inserted_id)

def update_room_count(id_string, count, use_room_name=False):
    if not use_room_name:
        qry = {"_id": ObjectId(id_string)}
    else:
        qry = {"room" : id_string}
    status = room_collection.update_one(qry, {"$inc":{"roomCount": count, "stateId": 1}})

def get_room_state(id_string):
    res = room_collection.find_one({"_id": ObjectId(id_string)})
    if res is not None:
        res = {k: v for k, v in res.items() if k not in ['lastUpdate']}
        res["_id"] = str(res["_id"])
    return res
