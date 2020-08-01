from flask import Flask, request, Response
from flask_socketio import SocketIO, join_room, leave_room, emit, rooms
from utils import load_ultimates, load_ability_details_by_id, load_hero_ability_ids
from pymongo.mongo_client import MongoClient
import simplejson
import humps
import string
import random
from mongo_helpers import update_room, get_room_state, create_room, get_active_room

def get_random_room():
    return ''.join(random.choice(string.ascii_uppercase) for i in range(5))


def leave_rooms():
    user_rooms = rooms(request.sid, '/')
    if len(user_rooms) > 1:
        for room in user_rooms:
            leave_room(room, request.sid, '/')
    return


app = Flask(__name__)
__VERSION__ = '0.1a'
ults = load_ultimates()
heroes = load_hero_ability_ids()
abilities_by_id = load_ability_details_by_id()
client = MongoClient()
db = client.get_database("dota")
ability_stats = db.get_collection("abilities")
socketio = SocketIO(app)


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
    if state is not None:
        oldState = get_room_state(state["_id"])
        print(state["stateId"])
        print(oldState["stateId"])
        if oldState["stateId"] == state["stateId"] or True:
            state["stateId"] += 1
            status = update_room(state["_id"], state)
            print(status.modified_count)
            print(state)
            emit("stateUpdated", state, room=state["room"])
        else:
            emit("stateUpdated", oldState, room=state["room"])


@socketio.on("createRoom")
def socket_create_room(state=None):
    if state is None:
        return
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


@app.route('/api/getSkills', methods=['POST'])
def get_skills():
    abilities = request.json
    print(abilities)
    skills = []
    fields = ("ability_name", "behavior", "desc", "img", "dname")
    for ab_id in abilities:
        skill_details = {k: v for k, v in abilities_by_id[ab_id].items() if k in fields}
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
        if skill_details["stats"] == None:
            continue
        skills.append(skill_details)
    return Response(simplejson.dumps(humps.camelize(skills), ignore_nan=True), mimetype="application/json")


@app.route('/api/hero/<int:hero_id>')
def load_hero(hero_id):
    fields = ("ability_name", "behavior", "desc", "img", "dname")

    skill_ids = [heroes[hero_id]]
    hero_skills = []
    for ab_id in skill_ids:
        skill_details = {k: v for k, v in abilities_by_id[ab_id].items() if k in fields}
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
        if skill_details["stats"] == None:
            continue
        hero_skills.append(skill_details)

    return simplejson.dumps(humps.camelize(hero_skills), ignore_nan=True)


if __name__ == '__main__':
    socketio.run(app)
