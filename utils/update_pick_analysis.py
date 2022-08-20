from pick_analysis import NoSkillDataException, PickAnalysis
from constant_loaders import load_ability_details_by_id
from tqdm import tqdm

pick = PickAnalysis()
id_lu = load_ability_details_by_id()

PickAnalysis().combo_picks()

for id in tqdm(pick.get_distinct_abilities()):
    try:
        pick.set_pick_id(id).save_pick_analytics()
    except NoSkillDataException:
        skill = id_lu[id]
        name = skill["dname"] if type(skill) == dict else skill
        print(f"No Skill Data for {name} ({id})")
        continue
