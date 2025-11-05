from pydantic import BaseModel

# ---------------- AUTH MODELS ----------------
class UserSignup(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# ---------------- CHAT MODEL ----------------
class ChatRequest(BaseModel):
    query: str

# ---------------- SAVE ANSWER MODEL ----------------
class SaveAnswerRequest(BaseModel):
    chat_id: str
