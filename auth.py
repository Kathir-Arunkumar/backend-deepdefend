import hashlib
from fastapi import APIRouter, HTTPException
from models import UserSignup, UserLogin
from database import users_collection

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

    # Hash the password before storing
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

    return {"message": "Login successful!"}