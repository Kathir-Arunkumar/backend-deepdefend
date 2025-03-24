from pydantic import BaseModel, EmailStr
from typing import Optional

# User Signup Schema
class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str

# User Login Schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# File Metadata Schema
class FileMetadata(BaseModel):
    user_id: str  # Owner of the file
    file_name: str
    file_type: str
    file_size: int
    storage_path: Optional[str] = None  # Where the file is stored