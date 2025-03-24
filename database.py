from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB Atlas
client = AsyncIOMotorClient(MONGO_URI)
db = client["login_system"]  # Database Name
users_collection = db["users"]  # Users Collection
files_collection = db["files"]  # Files Collection 