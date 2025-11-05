from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["chatbot_db"]

users_collection = db["users"]
chats_collection = db["chats"]
saved_collection = db["saved_answers"]
