from fastapi import WebSocket 
import logging
import json
from app.db.query import execute_query, insert_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id in self.active_connections:
            logger.warning(f"User {user_id} is already connected.")
            return

        query = "UPDATE users SET status = 'Online' WHERE id = $1 RETURNING id"
        try:
            result = await execute_query(insert_query, query, user_id)
            if result:
                self.active_connections[user_id] = websocket
                await self.notify_status_change(user_id, "Online")
                logger.info(f"User {user_id} connected")
        except Exception as e:
            logger.error(f"Failed to connect user {user_id}: {e}")

    async def disconnect(self, user_id: int):
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} is not connected.")
            return

        query = "UPDATE users SET status = 'Offline' WHERE id = $1 RETURNING id"
        try:
            result = await execute_query(insert_query, query, user_id)
            if result:
                self.active_connections.pop(user_id)
                await self.notify_status_change(user_id, "Offline")
                logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect user {user_id}: {e}")

    async def notify_status_change(self, user_id: int, status: str):
        message = json.dumps({'type': 'status', 'user_id': user_id, 'status': status})
        for connection_id, connection in self.active_connections.items():
            if connection_id != user_id:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to notify status change to {connection_id}: {e}")

    async def send_message(self, result):
        websocket = self.active_connections.get(result['receiver_id'])
        if websocket:
            try:
                await websocket.send_text(json.dumps({'type': 'chat', **result}))
                logger.info(f"Sent message from {result['sender_id']} to {result['receiver_id']}")
            except Exception as e:
                logger.error(f"Failed to send message to {result['receiver_id']}: {e}")

    async def update_msg_status(self, user_id: int, uuid: str, event: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps({'type': 'msgupdate', 'uuid': uuid, 'event': event}))
            except Exception as e:
                logger.error(f"Failed to update message status for {user_id}: {e}")

    async def typingIndicator(self, type: str, receiver_id: int, sender_id: int):
        websocket = self.active_connections.get(receiver_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps({'type': type, 'sender_id': sender_id}))
            except Exception as e:
                logger.error(f"Failed to send typing indicator to {receiver_id}: {e}")

manager = ConnectionManager()
