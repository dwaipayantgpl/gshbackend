import socketio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app=socketio.ASGIApp(sio)

online_users={}

@sio.event
async def connect(sid,environ):
    print(f"Socket connected:{sid}")

@sio.event
async def register(sid,data):
    user_id=data.get("user_id")
    if user_id:
        online_users[user_id]=sid
        print(f"User {user_id} is now online.")

@sio.event
async def disconnect(sid):
    for uid, s in list(online_users.items()):
        if s==sid:
            del online_users[uid]
            print(f"User {uid} went offline")
            break
        