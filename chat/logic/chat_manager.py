# from fastapi import WebSocket
# from typing import Dict, List

# class ChatManager:
#     def __init__(self):
#         self.active_connections: Dict[str, List[WebSocket]] = {}

#     async def connect(self, websocket: WebSocket, booking_id: str):
#         #await websocket.accept()
#         if booking_id not in self.active_connections:
#             self.active_connections[booking_id] = []
#         self.active_connections[booking_id].append(websocket)

#     def disconnect(self, websocket: WebSocket, booking_id: str):
#         self.active_connections[booking_id].remove(websocket)
#         if not self.active_connections[booking_id]:
#             del self.active_connections[booking_id]

#     async def send_personal_message(self, message: dict, websocket: WebSocket):
#         await websocket.send_json(message)

#     async def broadcast_to_room(self, booking_id: str, message: dict):
#         if booking_id in self.active_connections:
#             for connection in self.active_connections[booking_id]:
#                 await connection.send_json(message)

# manager = ChatManager()



from fastapi import WebSocket
from typing import Dict, List

class ChatManager:
    def __init__(self):
        # Structure: { "booking_id": { "registration_id": [ws1, ws2] } }
        self.rooms: Dict[str, Dict[str, List[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, booking_id: str, registration_id: str):
        if booking_id not in self.rooms:
            self.rooms[booking_id] = {}
        
        if registration_id not in self.rooms[booking_id]:
            self.rooms[booking_id][registration_id] = []
            
        self.rooms[booking_id][registration_id].append(websocket)

    def disconnect(self, websocket: WebSocket, booking_id: str, registration_id: str):
        if booking_id in self.rooms and registration_id in self.rooms[booking_id]:
            self.rooms[booking_id][registration_id].remove(websocket)
            
            # Senior's Rule: If no more sockets for this user, remove user_id
            if not self.rooms[booking_id][registration_id]:
                del self.rooms[booking_id][registration_id]
            
            # If no more users in the booking, remove booking_id
            if not self.rooms[booking_id]:
                del self.rooms[booking_id]

    async def broadcast_to_booking(self, booking_id: str, message: dict):
        """Sends to EVERYONE (all devices of both users) in the booking"""
        if booking_id in self.rooms:
            for user_id in self.rooms[booking_id]:
                for connection in self.rooms[booking_id][user_id]:
                    try:
                        await connection.send_json(message)
                    except:
                        continue

manager = ChatManager()