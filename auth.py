# auth.py
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from database import users_collection
from bson import ObjectId

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "secret123")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

security = HTTPBearer()

def create_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# ✅ FIXED HERE — use `data` dict instead of separate args
def create_access_token(data: dict):
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + timedelta(hours=24)})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    user = users_collection.find_one({"_id": ObjectId(payload["user_id"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"user_id": str(user["_id"]), "email": user["email"]}
