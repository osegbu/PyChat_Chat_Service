from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv, dotenv_values
import os

load_dotenv()

API_KEY = os.getenv('API_KEY')
api_key_header = APIKeyHeader(name='x-api-key')

async def check_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Api Key")