from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import jwt
import datetime
import os

# 🌐 Allowed origins (IMPORTANT: No "*")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://chatbot-webapp.vercel.app",  # ✅ Your Vercel frontend deployment URL
]

app = FastAPI()

# ✅ Correct CORS setup (DO NOT CHANGE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Config
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = "HS256"

# Model Schemas
class User(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None

def create_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(lambda: None)):
    from fastapi import Request
    request = Request(scope={"type": "http"})
    token = request.headers.get("Authorization")

    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    try:
        token = token.replace("Bearer ", "")
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
def home():
    return {"message": "Backend working ✅"}

@app.post("/signup")
def signup(user: User):
    print(f"New Signup: {user.email}")
    token = create_token(user.email)
    return {"token": token}

@app.post("/login")
def login(user: User):
    print(f"Login Request: {user.email}")
    token = create_token(user.email)
    return {"token": token}

@app.post("/chat")
def chat(request: ChatRequest, email: str = Depends(get_current_user)):
    print(f"User: {email}, Message: {request.message}")

    # Mock reply (replace with OpenAI / Groq / Render API later)
    return {"reply": f"AI Reply for: {request.message}"}
