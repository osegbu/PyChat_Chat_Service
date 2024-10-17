import aiosqlite
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
from datetime import datetime
import base64
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from app.websocket.connectionmanager import ConnectionManager
from app.models.validations import ImageUpload
import aiofiles
from app.routes.chat_route import chat_router
from app.routes.login_route import login_router
from app.routes.signup_router import signup_router
from app.routes.logout_router import logout_router
from app.routes.get_users_router import get_users_router


load_dotenv()

if not os.path.exists("./static"):
    os.makedirs("./static")

SECRET_KEY = os.getenv("AUTH_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
WEBSOCKET_TIMEOUT = int(os.getenv("WEBSOCKET_TIMEOUT"))
REDIS_URL = os.getenv("REDIS_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global manager
    global chatdb
    async with aiosqlite.connect("pychat.db") as db:
        chatdb = db
        await db.execute('''
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            uuid TEXT NOT NULL UNIQUE,
            image TEXT,
            message TEXT
        );
        ''')
        await db.execute('''
        CREATE INDEX IF NOT EXISTS privatechat_sender_receiver 
        ON chat(sender_id, receiver_id);
        ''')
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            profileimage TEXT NOT NULL,
            password TEXT NOT NULL,
            status TEXT DEFAULT 'Online'
        );
        ''')
        await db.commit()
        manager = ConnectionManager(REDIS_URL, chatdb)
        await manager.init_redis()
        print("Database and Redis initialized")
        app.include_router(chat_router(chatdb))
        app.include_router(login_router(chatdb))
        app.include_router(signup_router(chatdb))
        app.include_router(logout_router(chatdb))
        app.include_router(get_users_router(chatdb))

        yield
        
        await manager.close_redis()
        print("Server and Redis shutting down...")

app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory='./static'), name='static')

origins = [os.getenv("AUTH_URL")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=WEBSOCKET_TIMEOUT)
                await handle_received_data(websocket, data)
            except asyncio.TimeoutError:
                print(f"No ping received from user {user_id}, closing WebSocket")
                await websocket.close()
                await manager.disconnect(user_id)
                break
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        print(f"User {user_id} disconnected from {websocket.client}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"Cleaned up connection for user {user_id}")

async def handle_received_data(websocket: WebSocket, data: str):
    try:
        json_data = json.loads(data)
        message_type = json_data.get('type')

        if message_type == 'chat':
            await handle_chat(json_data)
        elif message_type in ['typing', 'blur']:
            await manager.typing_indicator(message_type, json_data['receiver_id'], json_data['sender_id'])
        elif message_type == 'ping':
            await websocket.send_text(json.dumps({'type': 'pong', 'user_id': json_data['user_id']}))
        elif message_type == 'ack':
            await manager.acknowledge_message(json_data['message_id'], int(json_data['receiver_id']))
    except json.JSONDecodeError:
        print("Received invalid JSON data")
    except KeyError as e:
        print(f"Missing key in received data: {e}")
    except Exception as e:
        print(f"Unexpected error while handling data: {e}")

async def handle_chat(json_data: dict):
    try:
        sender_id = int(json_data['sender_id'])
        receiver_id = int(json_data['receiver_id'])
        message = json_data['message']
        uuid = json_data['uuid']
        timestamp = json_data['timestamp']
        file_data = json_data.get('file')

        image_url = None
        if file_data:
            image_url = await handle_file_upload(file_data)

        query = '''
            INSERT INTO chat(sender_id, receiver_id, message, timestamp, uuid, image) 
            VALUES (?, ?, ?, ?, ?, ?) 
            RETURNING id, sender_id, receiver_id, message, timestamp, uuid, image
        '''
        try:
            async with chatdb.execute(query, (sender_id, receiver_id, message, timestamp, uuid, image_url)) as cursor:
                chat_message = await cursor.fetchone()
                await chatdb.commit()
            
                if chat_message:
                    await manager.update_msg_status(sender_id, uuid, "sent")

                    if sender_id != receiver_id:
                        chat = {
                            'id': chat_message[0], 
                            'sender_id': chat_message[1], 
                            'receiver_id': chat_message[2], 
                            'message': chat_message[3], 
                            'timestamp': chat_message[4], 
                            'uuid': chat_message[5], 
                            'image': chat_message[6]
                        }
                        await manager.send_message(chat)
                        print(f"Message sent from user {sender_id} to {receiver_id}")

        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: chat.uuid" in str(e):
                await manager.update_msg_status(sender_id, uuid, "sent")
            else:
                raise
    except Exception as e:
        print(f"Error handling chat message: {e}")

async def handle_file_upload(file_data: dict):
    try:
        file_name = file_data['name']
        file_type = file_data['type']
        file_size = file_data['size']
        base64_data = file_data['data']

        ImageUpload(content_type=file_type, size=file_size)
        file_content = base64.b64decode(base64_data)

        unique_file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(file_name)[1]}"
        file_path = os.path.join("static", unique_file_name)
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return unique_file_name
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise
