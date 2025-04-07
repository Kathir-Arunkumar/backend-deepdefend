import hashlib
import os
from fastapi import APIRouter, HTTPException
from models import UserSignup, UserLogin
from database import users_collection
from jose import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env file
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")  # Now using env variable
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in the environment!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

auth_router = APIRouter()

# Function to hash password using SHA-256
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# User Signup Route
@auth_router.post("/signup")
async def signup(user: UserSignup):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    hashed_pw = hash_password(user.password)

    user_data = {
        "name": user.name,
        "email": user.email,
        "password": hashed_pw
    }

    await users_collection.insert_one(user_data)
    return {"message": "User registered successfully!"}

# User Login Route
@auth_router.post("/login")
async def login(user: UserLogin):
    db_user = await users_collection.find_one({"email": user.email})

    if not db_user or db_user["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Optional: Generate and return JWT token
    token_data = {"sub": str(db_user["_id"]), "email": db_user["email"]}
    access_token = create_access_token(data=token_data)

    return {
        "message": "Login successful!",
        "access_token": access_token,
        "token_type": "bearer"
    }
