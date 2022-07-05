import json


def load_ability_id_lookup():
    with open('utils/dotaconstants/build/ability_ids.json', 'r') as f:
        ability_ids = json.load(f)
        ability_id_lookup = {v: int(k) for k, v in ability_ids.items()}
    return ability_id_lookup


def load_abilty_details():
    with open('utils/dotaconstants/build/abilities.json', 'r') as f:
        abilities_by_name: dict = json.load(f)

    id_lookup = load_ability_id_lookup()
    abilities_by_id = dict()
    for key, values in abilities_by_name.items():
        try:
            abilities_by_id.update({id_lookup[key]: {"ability_name": key, **values}})
            abilities_by_name[key].update({"id": id_lookup[key]})
        except KeyError:
            print(f"Could not add ability id for {key}")
    return abilities_by_name, abilities_by_id


def load_ability_details_by_name():
    return load_abilty_details()[0]


def load_ability_details_by_id():
    return load_abilty_details()[1]


def load_hero_by_name():
    with open('utils/dotaconstants/build/hero_names.json', 'r') as f:
        hero_details_by_name: dict = json.load(f)
    return hero_details_by_name


def load_hero_by_id():
    with open('utils/dotaconstants/build/heroes.json', 'r') as f:
        hero_details_by_id: dict = json.load(f)
    return hero_details_by_id


def load_heroes_abilities_by_name():
    with open('utils/dotaconstants/build/hero_abilities.json', 'r') as f:
        hero_abilities: dict = json.load(f)
    return hero_abilities


def load_heroes_abilities_by_id():
    hero_abilities = load_heroes_abilities_by_name()
    heroes = load_hero_by_name()
    abilities = load_ability_details_by_name()
    hero_abilities_by_id = dict()
    for key, item in hero_abilities.items():
        item.update({"abilities": [abilities[name]['id'] for name in item['abilities']]})
        hero_abilities_by_id.update({heroes[key]['id']: item})
    return hero_abilities_by_id


def load_hero_ability_list():
    with open('resources/hero_skills.json', 'r') as f:
        hero_skills: dict = json.load(f)
    return hero_skills


def load_hero_ability_ids():
    hero_ab = load_hero_ability_list()
    hero_name = load_hero_by_name()
    ab_name = load_ability_details_by_name()
    heroes = {}
    for hero, skills in hero_ab.items():
        try:
            hero_id = hero_name[hero]["id"]
            heroes[hero_id] = [ab_name[skill]["id"] if skill is not None else None for skill in skills]
        except KeyError:
            print(f"Skipping {hero}")
    return heroes

def load_list_ad_abilitity_ids():
    hero_ab = load_hero_ability_list()
    ability_list = load_ability_id_lookup()
    ability_names = []
    for hero, skills in hero_ab.items():
        ability_names.extend(skills)
    return [ability_list[name] for name in ability_names if name in ability_list]

def load_ultimates():
    hero_abs = load_heroes_abilities_by_id()
    hero_ab_list = load_hero_ability_ids()
    abilities = load_ability_details_by_id()
    heroes = load_hero_by_id()

    ultimates = list()
    for hero_id, hero in hero_abs.items():
        try:
            hero_details = heroes[str(hero_id)]
            ability_id = hero_ab_list[hero_id][3]
            if ability_id is None:
                continue
            ultimates.append(dict(
                heroId=hero_id,
                heroAbilities=hero_ab_list[hero_id],
                heroName=hero_details["localized_name"],
                abilityId=ability_id,
                abilityName=abilities[ability_id]['dname'],
            ))
        except KeyError:
            print("Did not load {hero}")
    return dict(ultimates=ultimates)


if __name__ == '__main__':
    ults = load_ultimates()
    pass
