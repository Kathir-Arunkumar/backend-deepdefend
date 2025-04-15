from pydantic import BaseModel, EmailStr
from typing import Optional, List

#  User Signup Schema
class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str

#  User Login Schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# File Metadata Schema (used in DB)
class FileMetadata(BaseModel):
    file_name: str
    file_type: str
    file_size: int
    storage_path: Optional[str] = None
    extracted_text: str
    indexed: Optional[bool] = False
    chunk_count: Optional[int] = 0

# Chatbot Query Schema
class QueryRequest(BaseModel):
    file_name: Optional[str] = None
    query: str

# Search Request Schema
class SearchRequest(BaseModel):
    query: str

# Search Response Models
class SearchResult(BaseModel):
    file_name: str
    snippet: str
    score: float

class SearchResponse(BaseModel):
    matches: List[SearchResult]
