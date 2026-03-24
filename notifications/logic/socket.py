
from typing import Dict, List
from fastapi import WebSocket

class NotificationManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"✅ User {user_id} connected for notifications.")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"❌ User {user_id} offline.")

    async def send_to_user(self, user_id: str, message: dict):
        """Push notification to a specific user automatically"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    continue

    async def broadcast(self, message: dict):
        """Push notification to EVERYONE online (Admin Case)"""
        for user_id in self.active_connections:
            await self.send_to_user(user_id, message)

notif_manager = NotificationManager()