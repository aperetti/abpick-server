from flask import Flask, request, Response
from flask_socketio import SocketIO, join_room, leave_room, emit, rooms
from utils import load_ultimates, load_ability_details_by_id, load_hero_ability_ids, parse_heroes, Predictor, load_hero_by_id
from pymongo.mongo_client import MongoClient
import simplejson
import humps
import string
import random
from mongo_helpers import update_room, get_room_state, create_room, get_active_room
from functools import lru_cache
from xgboost import XGBRegressor
from bson.objectid import ObjectId


def get_random_room():
    return ''.join(random.choice(string.ascii_uppercase) for i in range(5))


def verify_state(state, room_state=None):
    try:

        if any([
            len(state["skills"]) > 48,
            len(state["pickHistory"]) > 48,
            not isinstance(state["stateId"], int),
            state["stateId"] > 100000,
            not isinstance(state["room"], str),
            room_state is not None and state["stateId"] < room_state["stateId"],
            len(state["room"]) > 5,
            *[x is not None and not isinstance(x, int)
              for x in state["skills"]],
            *[x is not None and not isinstance(x, int) for x in state["pickHistory"]]
        ]):
            print("State Failed to Validate")
            return False
        else:
            return True
    except KeyError:
        return False


def leave_rooms():
    user_rooms = rooms(request.sid, '/')
    for room in user_rooms:
        if room == request.sid:
            continue
        leave_room(room, request.sid, '/')
    return


@lru_cache(maxsize=None)
def load_skill(ab_id):
    if ab_id == None:
        return {
            "ability_id": -1,
            "ability_name": "needs_selection",
            "behavior": None,
            "desc": None,
            "img": None,
            "dname": "Needs Selection",
            "stats": {
                'mean': 0,
                'pick_rate': 0,
                'pick_rate_rounds': [],
                'std': 0,
                'win_rate': 0,
                'win_rate_rounds': [],
                'survival': []
            }
        }
    fields = ("ability_name", "behavior", "desc", "img", "dname")
    skill_details = {k: v for k,
                     v in abilities_by_id[ab_id].items() if k in fields}
    skill_details["ability_id"] = ab_id
    skill_details["stats"] = ability_stats.find_one(
        {"_id": ab_id},
        {
            'mean': 1,
            'pick_rate': 1,
            'pick_rate_rounds': 1,
            'std': 1,
            'win_rate': 1,
            'win_rate_rounds': 1,
            'survival': 1
        })
    return skill_details


def load_skills(abilities):
    skills = []
    for ab_id in abilities:
        try:
            skill_details = load_skill(ab_id)
            if skill_details["stats"] == None:
                continue
            skills.append(skill_details)
        except KeyError:
            continue
    return skills


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
__VERSION__ = '0.1a'
ults = load_ultimates()
heroes = load_hero_ability_ids()
hero_by_id = load_hero_by_id()
abilities_by_id = load_ability_details_by_id()
client = MongoClient()
db = client.get_database("dota")
ability_stats = db.get_collection("abilities")
socketio = SocketIO(app, cors_allowed_origins="*")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
predictor = Predictor()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@socketio.on('joinRoom')
def socket_join_room(room=None):
    if room is None:
        return
    room_details = get_active_room(room)
    if room_details is not None:
        leave_rooms()
        join_room(room)
        emit("roomJoined", room_details)


@socketio.on('updateState')
def socket_update_state(state=None):
    room_state = db.get_collection('rooms').find_one({'_id': ObjectId(state["_id"])})
    if room_state is None:
        return
    if verify_state(state, room_state):
        update_room(state["_id"], state)
        emit("stateUpdated", state, room=state["room"])
    else:
        room_state["_id"] = str(room_state["_id"])
        emit("stateUpdated", room_state, room=state["room"])


@socketio.on("createRoom")
def socket_create_room(state=None):
    if verify_state(state):
        leave_rooms()
        i = 0
        while i < 10:
            room = get_random_room()
            if get_active_room(room) is None:
                state["room"] = room
                id = create_room(state)
                state["_id"] = id
                join_room(room)
                emit("roomJoined", state)
                break
            i += 1
            if i == 10:
                emit("createRoomFailed")


@socketio.on("leaveRoom")
def socket_leave_room():
    leave_rooms()
    emit("roomLeft")


@app.route('/api')
def abpick_api():
    return f'API Version {__VERSION__}'


@app.route('/api/ultimates')
def load_ultimates():
    return ults


@app.route('/api/parseConsole', methods=['POST'])
def parse_console():
    console_log = request.get_data().decode('utf-8')
    hero_ids = parse_heroes(console_log)
    game_heroes = []
    for hero_id in hero_ids:
        skill_ids = heroes[int(hero_id)]
        hero_skills = load_skills(skill_ids)
        game_heroes.append(hero_skills)

    return simplejson.dumps(humps.camelize(game_heroes), ignore_nan=True)


@app.route('/api/getSkills', methods=['POST'])
def get_skills():
    abilities = request.json
    skills = load_skills(abilities)
    return Response(simplejson.dumps(humps.camelize(skills), ignore_nan=True), mimetype="application/json")


# @app.route('/api/postBoard', methods=['POST'])
# def post_board():
#     if 'file' not in request.files:
#         return {
#             "error": "File not found",
#         }
#     file = request.files['file']
#     # if user does not select file, browser also
#     # submit an empty part without filename
#     if file.filename == '':
#         return {
#             "error": "No file was uploaded",
#         }

#     if file and allowed_file(file.filename):
#         try:
#             skills = detect_skills(file)
#             return {
#                 "result": skills
#             }
#         except ResolutionException:
#             return {
#                 "error": "Resolution must be 1920x1080."
#             }
#         except Exception as e:
#             print(e)
#             return {
#                 "error": "Could not process image."
#             }

@app.route('/api/hero/<int:hero_id>')
def load_hero(hero_id):
    skill_ids = heroes[hero_id]
    hero_skills = load_skills(skill_ids)
    return simplejson.dumps(humps.camelize(hero_skills), ignore_nan=True)


@app.route('/api/hero')
def load_all_heroes():
    skill_dict = {}
    hero_dict = {}
    for hero, skills in heroes.items():
        hero_dict[hero] = hero_by_id[str(hero)]["localized_name"]
        skill_dict[hero] = load_skills(skills)
    res = {
        "skill_dict": skill_dict,
        "hero_dict": hero_dict
    }
    return simplejson.dumps(humps.camelize(res), ignore_nan=True)


@app.route('/api/predict', methods=['POST'])
def predict():
    req = request.json
    res = predictor.predict(req["picked"], req["available"])
    return simplejson.dumps(humps.camelize(res), ignore_nan=True)


if __name__ == '__main__':
    socketio.run(app)
