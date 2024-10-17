from fastapi import APIRouter, Depends, HTTPException, status
import bcrypt
from app.utils.checkapikey import check_api_key
from app.models.validations import LoginRequest

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def login_router(chatdb):
    router = APIRouter()

    @router.post("/login", description="Login a user with their username and password")
    async def login_endpoint(login_request: LoginRequest, api_key: str = Depends(check_api_key)):
        try:
            query = "SELECT * FROM users WHERE username = ?"
            async with chatdb.execute(query, (login_request.username.lower(),)) as cursor:
                user = await cursor.fetchone()
                if user and verify_password(login_request.password, user[3]):
                    user_list = list(user)
                    user_list.pop(3)
                    user_data = {'id' : user_list[0],
                                'username' : user_list[1],
                                'profileimage' : user_list[2]}
                    return user_data
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid credentials')
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return router