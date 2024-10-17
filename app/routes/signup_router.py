from fastapi import APIRouter, Depends, HTTPException, status
import bcrypt
from datetime import datetime
from app.utils.checkapikey import check_api_key
from app.models.validations import CreatUser
from app.utils.create_avatar import avatar
import os

async def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_passwords_match(password: str, confirm_password: str):
    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    return password

def signup_router(chatdb):
    router = APIRouter()

    @router.post("/signup", description="Create a new user with a username and password.")
    async def signup_endpoint(create_user: CreatUser, api_key: str = Depends(check_api_key)):
        try:
            username = create_user.username.lower()
            first_letter = username[0].upper()
            password = await hash_password(check_passwords_match(create_user.password, create_user.confirm_password))
            image_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            avatar(first_letter, output_path=os.path.join("static", image_name))

            query = "INSERT INTO users(username, password, profileimage) VALUES (?, ?, ?) RETURNING id, username, profileimage"
            async with chatdb.execute(query, (username, password, image_name)) as cursor:
                user = await cursor.fetchone()
                await chatdb.commit()
                user_data = {'id' : user[0],
                            'username' : user[1],
                            'profileimage' : user[2]}
                return user_data
        except Exception as e:
            await chatdb.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return router