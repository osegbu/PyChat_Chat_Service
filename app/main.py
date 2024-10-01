from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Path, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import json
from datetime import datetime
import base64
import asyncio
from contextlib import asynccontextmanager

from app.utils.checkapikey import check_api_key
from app.websocket.connectionmanager import manager
from app.db.init_db import db_conn, db_close
from app.db.query import execute_query, insert_query, select_query
from app.models.validations import ImageUpload
import aiofiles
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

if not os.path.exists("./static"):
    os.makedirs("./static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_conn()
    logger.info("Server started...")
    yield
    await db_close()
    logger.info("Server shuting down...")

app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory='./static'), name='static')


origins = [
    os.getenv("HOST_URL")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

SECRET_KEY = os.getenv("AUTH_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
WEBSOCKET_TIMEOUT = int(os.getenv("WEBSOCKET_TIMEOUT"))


security = HTTPBearer()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=WEBSOCKET_TIMEOUT)
                await handle_received_data(websocket, data)
            except asyncio.TimeoutError:
                logger.warning(f"No ping received from user {user_id}, closing WebSocket")
                await websocket.close()
                await manager.disconnect(user_id)
                break
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected disconnected from {websocket.client}")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info(f"Cleaned up connection for user {user_id}")

async def handle_received_data(websocket: WebSocket, data: str):
    try:
        json_data = json.loads(data)
        message_type = json_data.get('type')

        if message_type == 'chat':
            await handleChat(json_data)
        elif message_type in ['typing', 'blur']:
            await manager.typingIndicator(message_type, json_data['receiver_id'], json_data['sender_id'])
        elif message_type == 'ping':
            await websocket.send_text(json.dumps({'type': 'pong', 'user_id': json_data['user_id']}))
    except json.JSONDecodeError:
        logger.error("Received invalid JSON data")
    except KeyError as e:
        logger.error(f"Missing key in received data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while handling data: {e}")


async def handleChat(json_data: dict):
    try:
        sender_id = int(json_data['sender_id'])
        receiver_id = int(json_data['receiver_id'])
        message = json_data['message']
        uuid = json_data['uuid']
        timestamp = json_data['timestamp']
        file_data = json_data.get('file')

        image_url = None
        if file_data:
            image_url = await handleFileUpload(file_data)
        
        query = """
        INSERT INTO chat(sender_id, receiver_id, message, timestamp, uuid, image) 
        VALUES ($1, $2, $3, $4, $5, $6) 
        RETURNING id, sender_id, receiver_id, message, timestamp, uuid, image
        """
        result = await execute_query(insert_query, query, sender_id, receiver_id, message, timestamp, uuid, image_url)
        
        if result:
            await manager.update_msg_status(sender_id, uuid, "sent")
            if sender_id != receiver_id:
                await manager.send_message(result)
                logger.info(f"Message sent from user {sender_id} to {receiver_id}")
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")


# File upload handler
async def handleFileUpload(file_data: dict):
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
        logger.error(f"Error uploading file: {e}")
        raise


@app.post("/load_chat/{id}", description="Load user's chat history")
async def load_chat(
    id: int = Path(..., description="The id of the user you want to load all chats", gt=0),
    api_key: str = Depends(check_api_key),
    credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload:
            if payload['id'] == str(id):
                query = """
                SELECT id, sender_id, receiver_id, message, timestamp, uuid, image
                FROM chat 
                WHERE sender_id=$1 OR receiver_id=$1 
                ORDER BY id
                """
                result = await execute_query(select_query, query, id)
                return result if result else []
    except Exception as e:
        print('failed')
        logger.error(f"Failed to load chat history for user {id}: {e}")
        raise
