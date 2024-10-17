from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.checkapikey import check_api_key

def get_users_router(chatdb):
    router = APIRouter()

    @router.post("/get_all_users")
    async def get_users(api_key: str = Depends(check_api_key)):
        try:
            query = "SELECT id, username, profileimage, status FROM users ORDER BY id DESC"
            async with chatdb.execute(query) as cursor:
                users = await cursor.fetchall()
                if users:
                    user_data = []

                    for user in users:
                        data = {'id' : user[0],
                                'username' : user[1],
                                'profileimage' : user[2],
                                'status' : user[3]}
                        user_data.append(data)
                    return user_data
                return []
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return router