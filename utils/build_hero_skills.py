from requests import get
from simplejson import dump

heroes = get('https://raw.githubusercontent.com/dotabuff/d2vpkr/master/dota/scripts/npc/npc_heroes.json').json()['DOTAHeroes']
abilities = get('https://raw.githubusercontent.com/dotabuff/d2vpkr/master/dota/scripts/npc/npc_abilities.json').json()[
    'DOTAAbilities']
hero_skills = {}


def is_ult(skill):
    try:
        ability = abilities[skill]
        return ability["AbilityType"] == "DOTA_ABILITY_TYPE_ULTIMATE"
    except KeyError:
        return False


for hero, data in heroes.items():
    if type(data) is not dict or hero in ['npc_dota_hero_base', 'npc_dota_hero_invoker']:
        continue
    skills = [None] * 4
    try:
        if "AbilityDraftAbilities" in data:
            for i, skill in enumerate(data["AbilityDraftAbilities"].values()):
                if is_ult(skill):
                    skills[3] = skill
                else:
                    skills[i] = skill
        else:
            for i, num in enumerate([1, 2, 3, 6]):
                skills[i] = data[f"Ability{num}"]
    except KeyError:
        print(f"Skipping {hero}")

    hero_skills[hero] = skills


dump(hero_skills, open("utils/build/hero_skills.json", 'w+'))
