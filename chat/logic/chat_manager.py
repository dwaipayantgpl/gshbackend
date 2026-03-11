from fastapi import WebSocket
from typing import Dict, List

class ChatManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, booking_id: str):
        await websocket.accept()
        if booking_id not in self.active_connections:
            self.active_connections[booking_id] = []
        self.active_connections[booking_id].append(websocket)

    def disconnect(self, websocket: WebSocket, booking_id: str):
        self.active_connections[booking_id].remove(websocket)
        if not self.active_connections[booking_id]:
            del self.active_connections[booking_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_room(self, booking_id: str, message: dict):
        if booking_id in self.active_connections:
            for connection in self.active_connections[booking_id]:
                await connection.send_json(message)

manager = ChatManager()