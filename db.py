from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")  # Store MongoDB URI in .env file
DB_NAME = "intro"

# Create MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db["components"]
users_collection = db["users"]
