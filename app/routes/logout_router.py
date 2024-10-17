from fastapi import APIRouter, Depends, Path
from app.utils.checkapikey import check_api_key

def logout_router(chatdb):
    router = APIRouter()

    @router.post("/logout/{id}", description="Log out a user")
    async def logout(id: int = Path(..., description="User ID to log out", gt=0), api_key: str = Depends(check_api_key)):
        query = "UPDATE users SET status = 'Offline' WHERE id = ?"
        async with chatdb.execute(query, (id,)) as cursor:
            await chatdb.commit()
            return {"detail": "User logged out"}
    return router