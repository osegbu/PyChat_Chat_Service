import uuid
import time
import json
import logging
import asyncio
from fastapi import WebSocket
from collections import defaultdict
from app.db.query import execute_query, insert_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.pending_messages: dict = {}
        asyncio.create_task(self.check_pending_messages())

    async def connect(self, websocket: WebSocket, user_id: int):
        """Handles user connection and updates their status to 'Online'."""
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
        """Handles user disconnection and updates their status to 'Offline'."""
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

    async def send_message(self, result):
        """Queues a chat message for delivery and retries if ACK not received."""
        websocket = self.active_connections.get(result['receiver_id'])
        if websocket:
            message_id = self.generate_message_id()
            message = json.dumps({'type': 'chat', 'message_id': message_id, **result})
            await self.queue_message(result['receiver_id'], message, message_id)

    async def update_msg_status(self, user_id: int, uuid: str, event: str):
        """Queues a message status update for delivery and retries if ACK not received."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                message_id = self.generate_message_id() 
                message = json.dumps({'type': 'msgupdate', 'uuid': uuid, 'event': event, 'message_id': message_id})
                await self.queue_message(user_id, message, message_id)
            except Exception as e:
                logger.error(f"Failed to update message status for {user_id}: {e}")

    async def typing_indicator(self, type: str, receiver_id: int, sender_id: int):
        """Queues a typing indicator for delivery and retries if ACK not received."""
        websocket = self.active_connections.get(receiver_id)
        if websocket:
            try:
                message_id = self.generate_message_id()
                message = json.dumps({'type': type, 'sender_id': sender_id, 'message_id': message_id})
                await self.queue_message(receiver_id, message, message_id)
            except Exception as e:
                logger.error(f"Failed to send typing indicator to {receiver_id}: {e}")

    async def queue_message(self, receiver_id: int, message: str, message_id: str, retries: int = 3, retry_interval: int = 5):
        """
        Queues a message for delivery and retries up to `retries` times if no ACK is received.
        This now uses a separate background task for retries.
        """
        self.pending_messages[message_id] = message
        websocket = self.active_connections.get(receiver_id)
        if not websocket:
            logger.warning(f"Receiver {receiver_id} is not connected.")
            return
        asyncio.create_task(self._retry_send_message(receiver_id, message, message_id, retries, retry_interval))

    async def _retry_send_message(self, receiver_id: int, message: str, message_id: str, retries: int, retry_interval: int):
        """
        Handles retrying to send a message in the background.
        """
        retry_count = 0
        while retry_count < retries:
            try:
                websocket = self.active_connections.get(receiver_id)
                if websocket:
                    await websocket.send_text(message)
                    logger.info(f"Sent message {message_id} to {receiver_id}, waiting for ACK...")

                    await asyncio.sleep(retry_interval)

                    if message_id not in self.pending_messages:
                        logger.info(f"Message {message_id} to {receiver_id} acknowledged")
                        return

                    retry_count += 1
                    logger.warning(f"Retrying message {message_id} to {receiver_id} (Attempt {retry_count})")
                else:
                    logger.warning(f"Receiver {receiver_id} is not connected, retry aborted")
                    break  
            except Exception as e:
                logger.error(f"Failed to send message {message_id} to {receiver_id}: {e}")
                break

        if message_id in self.pending_messages:
            logger.error(f"Failed to deliver message {message_id} to {receiver_id} after {retries} retries")

    async def acknowledge_message(self, message_id: str):
        """Handles acknowledgment (ACK) from the frontend for the given message."""
        if message_id in self.pending_messages:
            del self.pending_messages[message_id]
            logger.info(f"Message {message_id} acknowledged and removed from queue")

    async def check_pending_messages(self):
        """
        Periodically checks for pending messages that haven't been acknowledged.
        This can run in the background to retry sending pending messages.
        """
        while True:
            await asyncio.sleep(60)
            for message_id, message in list(self.pending_messages.items()):
                logger.warning(f"Message {message_id} is still pending, retrying...")
                await self._retry_send_message(message['receiver_id'], message, message_id, retries=3, retry_interval=5)

    def generate_message_id(self) -> str:
        """Generates a unique message ID using UUID and timestamp."""
        return f"{uuid.uuid4()}-{int(time.time())}"

    async def notify_status_change(self, user_id: int, status: str):
        """Notifies all users of a status change (Online/Offline) for the given user."""
        message_id = self.generate_message_id()
        message = json.dumps({'type': 'status', 'user_id': user_id, 'status': status, 'message_id': message_id})

        for connection_id in self.active_connections.keys():
            if connection_id != user_id:
                try:
                    await self.queue_message(connection_id, message, message_id)
                except Exception as e:
                    logger.error(f"Failed to notify status change to {connection_id}: {e}")

manager = ConnectionManager()
