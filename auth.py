from fastapi import APIRouter, HTTPException
from models import UserSignup, UserLogin
from database import users_collection
import bcrypt  # Using bcrypt directly

# Create an API router for authentication
auth_router = APIRouter()

# Function to hash passwords using bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Function to verify passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# User Signup Route
@auth_router.post("/signup")
async def signup(user: UserSignup):
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if passwords match
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Hash the password before storing
    hashed_pw = hash_password(user.password)

    # Create user document
    user_data = {
        "name": user.name,
        "email": user.email,
        "password": hashed_pw
    }

    # Insert into MongoDB
    await users_collection.insert_one(user_data)

    return {"message": "User registered successfully!"}

# User Login Route
@auth_router.post("/login")
async def login(user: UserLogin):
    # Find user in MongoDB
    db_user = await users_collection.find_one({"email": user.email})

    # Check if user exists and password is correct
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful!"}
