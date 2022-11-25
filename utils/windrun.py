import pandas as pd
import lxml.html as html
import requests
import numpy as np
from pymongo.mongo_client import MongoClient
from pymongo.collection import Collection

client = MongoClient()
db = client.get_database("dota")
abilities: Collection = db.get_collection("abilities")

abilities.update_many({}, {"$unset": {
    "scepter_pickup_rate": 1,
    "scepter_win_wo": 1,
    "scepter_win_w": 1,
    "shard_pickup_rate": 1,
    "shard_win_wo": 1,
    "shard_win_w": 1
}})

format_pct = lambda xs: [ None if x == '-' else float(x.strip().strip('%'))/100 for x in xs]
res = requests.get("https://windrun.io/ability-shifts")
doc = html.fromstring(res.content)
ids = [int(x.split("/")[2]) for x in doc.xpath('//*[@id="ability-shift-stats"]/tbody/tr/td[2]/a/@href')]
names = doc.xpath('//*[@id="ability-shift-stats"]/tbody/tr/td[2]/a/text()')
name_dict = dict(zip(names, ids))


res = requests.get("https://windrun.io/ability-aghs")
doc = html.fromstring(res.content)
ags_dict = {
    "abilities": [int(x.split("/")[2]) for x in doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[2]/a/@href')],
    "scepter_pickup_rate": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[3]/text()')),
    "scepter_win_wo": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[4]/text()')),
    "scepter_win_w": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[5]/text()')),
    "shard_pickup_rate": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[7]/text()')),
    "shard_win_wo": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[8]/text()')),
    "shard_win_w": format_pct(doc.xpath('//*[@id="ability-stats"]/tbody/tr/td[9]/text()')),
}
df = pd.DataFrame(ags_dict).set_index('abilities', inplace=False)


for id, record in df.to_dict('index').items():
    record = {k: v for k, v in record.items() if not pd.isna(v)}
    abilities.update_one({"_id": id}, {"$set": record})




# res = requests.get("https://windrun.io/ability-pairs")
# doc = html.fromstring(res.content)
# ags_dict = {
#     "abilities_1": [name_dict[x.strip()] for x in doc.xpath('//*[@id="ability-pair-stats"]/tbody/tr/td[2]/text()')],
#     "abilities_2": [name_dict[x.strip()] for x in doc.xpath('//*[@id="ability-pair-stats"]/tbody/tr/td[5]/text()')],
#     "sample_size": format_pct(doc.xpath('//*[@id="ability-pair-stats"]/tbody/tr/td[7]/text()')),
#     "win_pct": format_pct(doc.xpath('//*[@id="ability-pair-stats"]/tbody/tr/td[8]/text()')),
#     "synergy": format_pct(doc.xpath('//*[@id="ability-pair-stats"]/tbody/tr/td[9]/text()')),
# }
# df = pd.DataFrame(ags_dict)
# df['sample_size'] = df['sample_size'] * 100
# df1 = df.copy()
# df1.rename(columns={"abilities_1": "abilities_2", "abilities_2": "abilities_1"}, inplace=True)
# df = pd.concat([df, df1], axis=0)
# df['abilities_2'] = df['abilities_2'].astype(str)
# dfgs = df.groupby('abilities_1')
# for id, dfg in dfgs:
#     dfg = dfg.drop_duplicates(subset='abilities_2', keep='first')

#     combos = dfg.drop('abilities_1', axis=1).set_index('abilities_2', inplace=False).to_dict('index')
#     abilities.update_one({"_id": id}, {"$set": {"combos": combos}})