import logging
from logging.handlers import RotatingFileHandler
from time import sleep, time
from db import Database
from os import environ, makedirs
import pymongo
from requests import get
import logging

# Leverages the Dota API to grab the reads, not very effective.
makedirs("logs", exist_ok=True)

fl = RotatingFileHandler("logs/logs.log")
logging.basicConfig(handlers=[fl], level=logging.INFO, format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
logger = logging.getLogger("DotaWebAPI")


api_key = environ.get('DOTA_API_KEY')

db = Database()

matches_coll = db.db.get_collection('matches')

max = db.db.get_collection("max_parser")

max.update_one({"_id": 1}, {"$max": {"seq": 5626451107}}, upsert=True)


def get_max_id():
        return max.find_one({})["seq"]


while True:
    max_sequence = get_max_id()
    try:
        r = get(f"http://api.steampowered.com/IDOTA2Match_570/GetMatchHistoryBySequenceNum/v1?key={api_key}&start_at_match_seq_num={max_sequence}")
        res  = r.json()["result"]["matches"]
        for i, match in enumerate(res):
            try:
                if match["game_mode"] == 18:
                    match["_id"] = match["match_id"]
                    matches_coll.insert_one(match)
                    logger.info(f"Inserted match {match['_id']}")
                max.update_one({"_id": 1}, {"$max": {"seq": match["match_seq_num"]}})
            except BaseException as e:
                logger.error(f"Failed to insert {i} match, starting with {max_sequence}, {e}")
        max_sequence += 100
    except BaseException:
        logger.error(f"Failed to get response from {max_sequence}")
    finally:
        sleep(10)

