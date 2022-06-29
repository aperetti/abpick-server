# Ability Pick Tool

## Utilities

### Build Hero Skills - `utils/build_hero_skils.py`
Python script will pull the latest heroes and abilities from DotaBuff repository and build a new file `utils/build/hero_skills.json` for loading hero skill dictionary.

### Constant Loaders - `utils/constant_loaders.py`
Python script provides a set of convenient methods to pull relevant information from the build folder. It pulls data from:
 - `utils/build/ability_ids.json`
 - `utils/build/abilities.json`
 - `utils/build/hero_names.json`
 - `utils/build/heroes.json`
 - `utils/build/hero_abilities.json`
 - `utils/build/hero_skills.json`

### Database - `utils/db.py`
A class to help manage the mongo documents associated with parsing Open-Dota match details.

### Find Matches - `utils/find_matches.py`
Python script that will find new ability draft matches. It starts by pulling recently played matches from players that are known to play ability draft. Will add those matches and mark that the match has not been parsed.

### Grabber - `utils/grabber.py`
Python script will load the latest abilities from the build folder and then grab the associated icons from Dota

### Pick Analysis - `utils/pick_analysis.py`
Python script that will analyze all of the recent pick data and summarize the data for display by the client.

### Skill Detect (WIP) - `utils/skill_detector.py`
Python script that attempts extract the skills from the image.

### Update Pick Analysis - `util/update_pick_analysis.py`
Iterates throug the abilities and runs the analysis for each skills