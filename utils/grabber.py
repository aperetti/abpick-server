import shutil
from requests import get, HTTPError
import json
from utils import load_ability_details_by_id


def get_abilities():
    for id, details in load_ability_details_by_id().items():
        if "dname" not in details:
            continue
        try:
            response = get(f'http://media.steampowered.com{details["img"]}', stream=True)
            response.raise_for_status()
            with open(f'resources/abilities/{id}.png', 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        except KeyError as e:
            print(f'Skipping {details["ability_name"]} could not lookup')
        except HTTPError as e:
            print(f'Skipping {details["ability_name"]} could not access url')


if __name__ == "__main__":
    get_abilities()
