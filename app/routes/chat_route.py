from fastapi import APIRouter, Depends, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.checkapikey import check_api_key
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()

def chat_router(chatdb):
    router = APIRouter()
    SECRET_KEY = os.getenv("AUTH_SECRET")
    ALGORITHM = os.getenv("ALGORITHM")

    security = HTTPBearer()

    @router.post("/load_chat/{id}")
    async def load_chat(
        id: int = Path(..., gt=0),
        api_key: str = Depends(check_api_key),
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload and payload['id'] == str(id):
                query = '''
                SELECT id, sender_id, receiver_id, message, timestamp, uuid, image
                FROM chat 
                WHERE sender_id=? OR receiver_id=? 
                ORDER BY timestamp DESC
                '''
                async with chatdb.execute(query, (id, id)) as cursor:
                    chats = await cursor.fetchall()
                    if chats:
                        chat_data = []
                        for chat in chats:
                            message = {
                                'id': chat[0], 
                                'sender_id': chat[1], 
                                'receiver_id': chat[2], 
                                'message': chat[3], 
                                'timestamp': chat[4], 
                                'uuid': chat[5], 
                                'image': chat[6],
                                'status': 'sent'
                            }
                            chat_data.append(message)
                        return chat_data
                    else:
                        return []
        except Exception as e:
            print(f"Failed to load chat history for user {id}: {e}")
            raise

    return router

