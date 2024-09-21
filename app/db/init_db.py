from fastapi import HTTPException, status
import asyncpg
from dotenv import load_dotenv, dotenv_values
import os

load_dotenv()


db_user = os.getenv("DB_USER")
db_pwd = os.getenv("DB_PWD")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

class Database:
    def __init__(self, min_size=1, max_size=10) -> None:
        self.min_size = min_size
        self.max_size = max_size
        self.dsn = f"postgresql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}"
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def discount(self):
        if self.pool:
            await self.pool.close()
    
    async def acquire_connection(self):
        return await self.pool.acquire()

    async def release_connection(self, connection):
        await self.pool.release(connection)
                
                
database = Database() 

async def db_conn():
    try:
        await database.connect()
        print('Pool connected...')
        return {'Response': 'Connected'}
    except Exception as e:
        raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown error: {e}"
            )

async def db_close():
    await database.discount()
    print('Connection pool closed...')
    return {'Response': 'Disconnected'}