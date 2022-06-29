import shutil
from requests import get, HTTPError, exceptions as ex
import json
from constant_loaders import load_hero_ability_ids, load_ability_details_by_id
from time import sleep
import itertools
import glob

overloads = {
    5144: "/apps/dota2/images/abilities/riki_permanent_invisibility_md.png"
}

overload_icons = [5121]

def get_abilities(update=False):
    hero_skills = itertools.chain(*[skills for i, skills in load_hero_ability_ids().items()])
    skills = load_ability_details_by_id()
    for id in hero_skills:

        if update and len(glob.glob(f"resources/abilities/{id}.png")) > 0:
            continue

        if  id not in skills:
            print(f"Skipping ID {id}, skill not found")
            continue

        details = skills[id]

        if "dname" not in details:
            print(f"Skipping ID {id}, no dname found")
            continue

        sleep(.1)
        try:
            if id in overload_icons:
                shutil.copy(f'utils/overload_images/{id}.png', f'resources/abilities/{id}.png')
            else:
                    response = get(f'http://media.steampowered.com{overloads[id] if id in overloads else details["img"] }', stream=True)
                    response.raise_for_status()
                    with open(f'resources/abilities/{id}.png', 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                    del response
        except KeyError as e:
            print(f'Skipping {id} could not be found lookup')
        except (HTTPError, ex.InvalidURL)  as e:
            print(f'Skipping {details["ability_name"]} could not access url')


if __name__ == "__main__":
    get_abilities(True)
