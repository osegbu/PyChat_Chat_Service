from fastapi import  HTTPException, status
from pydantic import BaseModel, Field, field_validator

class ImageUpload(BaseModel):
    content_type: str = Field(..., description="The content type of the file.")
    size: int = Field(..., description="The size of the file in bytes.")

    @field_validator('content_type')
    def validate_content_type(cls, v):
        if v not in ['image/jpeg', 'image/png', 'image/gif']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail='Invalid image format. Only JPEG and PNG are supported.'
            )
        return v

    @field_validator('size')
    def validate_size(cls, v):
        max_size = 5 * 1024 * 1024  # 5 MB
        if v > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f'Image size exceeds the maximum limit of {max_size / (1024 * 1024)} MB.'
            )
        return v

class CreatUser(BaseModel):
    username: str = Field(..., description="The username of the user. It must not be empty.")
    password: str = Field(..., description="The password for the user. It must be at least 6 characters long.")
    confirm_password: str = Field(..., description="The confirmation of the password. It must match the password.")

    @field_validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must not be empty"
            )
        if len(v) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 4 characters long"
            )
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if not v or not v.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not be empty"
            )
        if len(v) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        return v
    
class LoginRequest(BaseModel):
    username: str = Field(..., description="The username of the user.")
    password: str = Field(..., description="The password of the user.")

    @field_validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must not be empty"
            )
        if len(v) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 4 characters long"
            )
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if not v or not v.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not be empty"
            )
        if len(v) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        return v