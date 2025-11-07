from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth import create_password_hash, verify_password, create_access_token, get_current_user
from database import users_collection, chats_collection
from dotenv import load_dotenv
import os
import requests
import base64
from bson import ObjectId

# -------------------- ENV SETUP --------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_MOCK_AI = os.getenv("USE_MOCK_AI", "false").lower() == "true"

# -------------------- FASTAPI APP --------------------
app = FastAPI(title="AI Chatbot with Vision + Multi-Chat")

# ✅ UPDATED CORS SETUP (Render + Vercel + Local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://chatbot-webapp.vercel.app",  # ✅ Your vercel frontend URL
        "*"  # ✅ Allow all origins as fallback (important for Render)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- DATA MODELS --------------------
class UserSignup(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    query: str
    chat_id: str = None


# -------------------- ROOT --------------------
@app.get("/")
def root():
    return {"message": "✅ Chatbot API running"}


# -------------------- AUTH ROUTES --------------------
@app.post("/signup")
def signup(user: UserSignup):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed_pw = create_password_hash(user.password)
    users_collection.insert_one({"email": user.email, "password": hashed_pw})
    return {"message": "Signup successful"}


@app.post("/login")
def login(user: UserLogin):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(
        data={"user_id": str(db_user["_id"]), "email": db_user["email"]}
    )
    return {"token": token}


# -------------------- CHAT ROUTES --------------------
@app.get("/chats")
def get_chats(user=Depends(get_current_user)):
    user_id = user["user_id"]
    chats = list(chats_collection.find({"user_id": user_id}, {"_id": 1, "title": 1}))
    for c in chats:
        c["_id"] = str(c["_id"])
    return {"chats": chats}


@app.post("/new-chat")
def new_chat(user=Depends(get_current_user)):
    user_id = user["user_id"]
    chat = {"user_id": user_id, "title": "Untitled Chat", "messages": []}
    result = chats_collection.insert_one(chat)
    chat["_id"] = str(result.inserted_id)
    return chat


@app.delete("/chat/{chat_id}")
def delete_chat(chat_id: str, user=Depends(get_current_user)):
    user_id = user["user_id"]
    result = chats_collection.delete_one({"_id": ObjectId(chat_id), "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found or unauthorized")
    return {"message": "Chat deleted"}


@app.get("/chat/{chat_id}")
def get_chat_messages(chat_id: str, user=Depends(get_current_user)):
    user_id = user["user_id"]
    chat = chats_collection.find_one({"_id": ObjectId(chat_id), "user_id": user_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or unauthorized")

    chat["_id"] = str(chat["_id"])
    return {"title": chat.get("title", "Untitled"), "messages": chat.get("messages", [])}


@app.post("/chat")
def chat(request: ChatRequest, user=Depends(get_current_user)):
    user_id = user["user_id"]

    if USE_MOCK_AI:
        return {"response": f"[Mock AI] You said: {request.query}"}

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API key")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": request.query},
                ],
            },
            timeout=60,
        )

        data = response.json()
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=str(data))

        answer = data["choices"][0]["message"]["content"]

        # ✅ Save messages to MongoDB
        if request.chat_id:
            chats_collection.update_one(
                {"_id": ObjectId(request.chat_id)},
                {"$push": {"messages": {"sender": "user", "text": request.query}}},
            )
            chats_collection.update_one(
                {"_id": ObjectId(request.chat_id)},
                {"$push": {"messages": {"sender": "bot", "text": answer}}},
            )

            # ✅ Auto title generation
            chat_doc = chats_collection.find_one({"_id": ObjectId(request.chat_id)})
            if chat_doc and chat_doc.get("title") == "Untitled Chat":
                title_preview = request.query[:30] + ("..." if len(request.query) > 30 else "")
                chats_collection.update_one(
                    {"_id": ObjectId(request.chat_id)},
                    {"$set": {"title": title_preview}},
                )

        return {"response": answer}

    except Exception as e:
        print("❌ Chat Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- IMAGE ANALYSIS --------------------
@app.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image."),
    chat_id: str = Form(None),
    user=Depends(get_current_user),
):
    user_id = user["user_id"]

    try:
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"},
                        ],
                    }
                ],
            },
            timeout=120,
        )

        data = response.json()
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=str(data))

        answer = data["choices"][0]["message"]["content"]

        if chat_id:
            chats_collection.update_one(
                {"_id": ObjectId(chat_id)},
                {"$push": {"messages": {"sender": "user", "text": prompt}}},
            )
            chats_collection.update_one(
                {"_id": ObjectId(chat_id)},
                {"$push": {"messages": {"sender": "bot", "text": answer}}},
            )

        return {"response": answer}

    except Exception as e:
        print("❌ Vision Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- TEST ROUTE --------------------
@app.get("/test-key")
def test_key():
    if not OPENAI_API_KEY:
        return {"success": False, "message": "No API key found"}
    return {"success": True, "message": "API key loaded successfully"}
