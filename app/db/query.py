from fastapi import HTTPException, status
import asyncio
import asyncpg
from app.db.init_db import database


timeOutMsg = ("The server took too long to respond to your request. " 
"Please try again later. If the issue persists, " 
"please contact our support team with the error details for further assistance.")

conErrorMsg = ("Sorry, we couldn't connect to the database right now. " 
"Please try again later. If the issue persists, " 
"please contact our support team with the error details for further assistance.")

internalErrorMsg = ("Internal server error. " 
"Please try again later. If the issue persists, " 
"please contact our support team with the error details for further assistance.")

async def insert_query(query, *args):
    connection = await database.acquire_connection()
    try:
        result = await asyncio.wait_for(
            connection.fetchrow(query, *args),
            timeout=300
        )
        return result
    finally:
        await database.release_connection(connection)

async def select_query(query, *args):
    connection = await database.acquire_connection()
    try:
        result = await asyncio.wait_for(
           connection.fetch(query, *args),
           timeout=300
        )
        return result
    finally:
        await database.release_connection(connection)


async def execute_query(func, query, *args, retires=3, delay=1, exceptions=(Exception)):
    attempt = 0
    while attempt < retires:
        try: 
            return await func(query, *args)
        except exceptions as e:
            if isinstance(e, asyncpg.UniqueViolationError):
                raise
            attempt += 1
            if attempt < retires:
                await asyncio.sleep(delay * attempt)
            else:
                if isinstance(e, asyncio.TimeoutError):
                    raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=timeOutMsg)
                if isinstance(e, asyncpg.PostgresConnectionError):
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=conErrorMsg)
                if isinstance(e, asyncpg.PostgresError):
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
                if isinstance(e, Exception):
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=internalErrorMsg)
