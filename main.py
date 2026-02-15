from fastapi import FastAPI, WebSocket,WebSocketDisconnect
from jose import jwt
from dotenv import load_dotenv
import os
import json
from database import get_user_friends

load_dotenv()

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")

ALGORITHM = "HS256"

app = FastAPI()
clients = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, ws: WebSocket, user_id: int):
        await ws.accept()
        self.active_connections[user_id] = ws

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_text(message)

    async def send_to_many(self, user_ids: list[int], message):
        for uid in user_ids:
            ws = self.active_connections.get(str(uid))
            print(f"websocket_id: {ws}")
            if ws:
                if isinstance(message, dict):
                    await ws.send_text(json.dumps(message))
                else:
                    await ws.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    token = ws.query_params.get("token")
    print(f"Token received: {token}")

    if not token:
        print("No token provided")
        await ws.close(code=1008)
        return

    try:
        print(f"Decoding with SECRET_KEY: {SECRET_KEY[:10]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Payload: {payload}")
        user_id = payload.get("user_id")
    except Exception as e:
        print(f"JWT Decode Error: {e}")
        await ws.close(code=1008)
        return

    await manager.connect(ws, user_id)

    try:
        print(manager.active_connections)
        while True:
            data = await ws.receive_json()

            event_type = data.get("type")

            if event_type == "status_update":
                reached_station = data.get("reached_station")
                
                friends_data = get_user_friends(user_id)
                
                # Flatten friends list in case it's nested
                friends = [f[0] for f in friends_data]
                print(friends)
                await manager.send_to_many(
                    friends,
                    {
                        "type": "friend_status",
                        "friend_id": user_id,
                        "reached": reached_station
                    }
                )

            if event_type == "arrived_station":

                station_id = data.get("station_id")

                if not station_id:
                    continue

                friends_data = get_user_friends(user_id)
                # Flatten friends list in case it's nested
                friends = [f[0] if isinstance(f, (list, tuple)) else f for f in friends_data] if friends_data else []

                await manager.send_to_many(
                    friends,
                    {
                        "type": "friend_status",
                        "friend_id": user_id,
                        "station_id": station_id
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(user_id)





