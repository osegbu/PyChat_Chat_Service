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