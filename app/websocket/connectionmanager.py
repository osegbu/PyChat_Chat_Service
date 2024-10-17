import uuid
import time
import json
import asyncio
from fastapi import WebSocket
from dotenv import load_dotenv
import aioredis

load_dotenv()

class ConnectionManager:
    def __init__(self, redis_url: str, db):
        self.redis = None
        self.redis_url = redis_url
        self.active_connections: dict = {}
        self.pending_messages: dict = {}
        self.db = db

    async def init_redis(self):
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            print("Connected to Redis")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")

    async def close_redis(self):
        if self.redis:
            await self.redis.close()
            print("Redis connection closed")

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id in self.active_connections:
            return
        self.active_connections[user_id] = websocket
        query = "UPDATE users SET status = 'Online' WHERE id = ? RETURNING id"
        try:
            async with self.db.execute(query, (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    await self.db.commit()
                    await self.notify_status_change(user_id, "Online")
                    await self.send_undelivered_messages(user_id)
        except Exception as e:
            print(f"Failed to connect user {user_id}: {e}")
            await self.db.rollback()

    async def disconnect(self, user_id: int):
        if user_id not in self.active_connections:
            return
        self.active_connections.pop(user_id)
        query = "UPDATE users SET status = 'Offline' WHERE id = ? RETURNING id"
        try:
            async with self.db.execute(query, (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    await self.db.commit()
                    await self.notify_status_change(user_id, "Offline")
        except Exception as e:
            print(f"Failed to disconnect user {user_id}: {e}")
            await self.db.rollback()

    async def store_in_redis(self, receiver_id: int, message_id: str, message: str):
        try:
            message_id = str(message_id)
            await self.redis.hset(f"undelivered:{receiver_id}", message_id, message)
            if message_id in self.pending_messages:
                del self.pending_messages[message_id]
        except Exception as e:
            print(f"Error storing message in Redis for receiver {receiver_id}, message_id {message_id}: {e}")

    async def retrieve_undelivered_messages(self, user_id: int):
        try:
            return await self.redis.hgetall(f"undelivered:{user_id}")
        except Exception as e:
            print(f"Failed to retrieve undelivered messages for user {user_id}: {e}")
            return {}

    async def delete_message_from_redis(self, receiver_id: int, message_id: str):
        try:
            await self.redis.hdel(f"undelivered:{receiver_id}", message_id)
        except Exception as e:
            print(f"Failed to delete message {message_id} from Redis for user {receiver_id}: {e}")

    async def send_message(self, result):
        websocket = self.active_connections.get(result['receiver_id'])
        message_id = self.generate_message_id()
        message = json.dumps({'type': 'chat', 'message_id': message_id, **result})

        if websocket:
            await self.queue_message(result['receiver_id'], message, message_id)
        else:
            await self.store_in_redis(result['receiver_id'], message_id, message)

    async def update_msg_status(self, user_id: int, uuid: str, event: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            message_id = self.generate_message_id()
            message = json.dumps({'type': 'msgupdate', 'uuid': uuid, 'event': event, 'message_id': message_id})
            await self.queue_message(user_id, message, message_id)

    async def typing_indicator(self, type: str, receiver_id: int, sender_id: int):
        websocket = self.active_connections.get(receiver_id)
        if websocket:
            try:
                message_id = self.generate_message_id()
                message = json.dumps({'type': type, 'sender_id': sender_id, 'message_id': message_id})
                await self.queue_message(receiver_id, message, message_id)
            except Exception as e:
                print(f"Failed to send typing indicator to {receiver_id}: {e}")

    async def acknowledge_message(self, message_id: str, receiver_id: int):
        if message_id in self.pending_messages:
            del self.pending_messages[message_id]

    async def send_undelivered_messages(self, user_id: int):
        undelivered_messages = await self.retrieve_undelivered_messages(user_id)
        for message_id, message in undelivered_messages.items():
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            try:
                id = json.loads(message)
                await self.queue_message(user_id, message, id['message_id'])
                await self.delete_message_from_redis(user_id, message_id)
            except json.JSONDecodeError as e:
                print(f"Failed to decode message with ID {message_id}: {e}")

    async def queue_message(self, receiver_id: int, message: str, message_id: str, retries: int = 5, retry_interval: int = 2):
        self.pending_messages[message_id] = message
        websocket = self.active_connections.get(receiver_id)
        if websocket:
            asyncio.create_task(self._retry_send_message(receiver_id, message, message_id, retries, retry_interval))

    async def _retry_send_message(self, receiver_id: int, message: str, message_id: str, retries: int, retry_interval: int):
        retry_count = 0
        while retry_count < retries:
            try:
                websocket = self.active_connections.get(receiver_id)
                if websocket:
                    await websocket.send_text(message)
                    await asyncio.sleep(retry_interval * (2 ** retry_count))

                    if message_id not in self.pending_messages:
                        return

                    retry_count += 1
                else:
                    if json.loads(message).get("type") == "chat":
                        await self.store_in_redis(receiver_id, message_id, message)
                    break
            except Exception as e:
                print(f"Failed to send message {message_id} to {receiver_id}: {e}")
                break

        if message_id in self.pending_messages:
            if json.loads(message).get("type") == "chat":
                await self.store_in_redis(receiver_id, message_id, message)
            else:
                del self.pending_messages[message_id]

    def generate_message_id(self) -> str:
        return f"{uuid.uuid4()}-{int(time.time())}"

    async def notify_status_change(self, user_id: int, status: str):
        message_id = self.generate_message_id()
        message = json.dumps({'type': 'status', 'user_id': user_id, 'status': status, 'message_id': message_id})

        for connection_id in self.active_connections.keys():
            if connection_id != user_id:
                await self.queue_message(connection_id, message, message_id)
