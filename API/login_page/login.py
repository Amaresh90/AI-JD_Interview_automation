from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from fastapi.responses import JSONResponse
from database.config import hr_collection
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from datetime import datetime

app = FastAPI()
login_router = APIRouter()

logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO")

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RESET_TOKEN_EXPIRE_MINUTES = 10  

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class User(BaseModel):
    email_id: str
    password: str

class forgotUser(BaseModel):
    email_id: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def create_token(email_id: str, user_id: str, role: str = "", expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    data = {
        "sub": email_id, 
        "id": str(user_id),
        "role": role,
        "exp": expire     
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def verify_token(token: str = Depends(oauth2_scheme)):
    """Used with Depends() for secured routes."""
    return decode_token(token)


def send_reset_email(email_id: str, reset_link: str):
    print(f"Sending password reset link to {email_id}: {reset_link}")


# middleware-----
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Only public endpoints
    public_paths = ["/login", "/openapi.json", "/docs", "/redoc"]
    
    for path in public_paths:
        if request.url.path.startswith(path):
            return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization header missing or invalid"})

    token = auth_header.split(" ")[1]
    try:
        decode_token(token)  
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return await call_next(request)


# Endpoints------------
# 1.login page
@login_router.post("/login")
def login_hr_user(login: User):
    user = hr_collection.find_one({"email_id": login.email_id})
    logger.info(f"user---> {user}")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not pwd_context.verify(login.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    token = create_token(email_id=login.email_id, user_id=str(user["_id"]), role=user["role"])
    return {
        "status_code": 200,
        "message": "Login successful",
        "access_token": token,
    }


# 2.Forget password (authenticated)
@login_router.post("/forget_password")
def forget_password(user: forgotUser, email_id: str = Depends(verify_token)):
    db_user = hr_collection.find_one({"email_id": user.email_id})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = create_token(
        email_id=user.email_id,
        user_id=str(db_user["_id"]),
        expires_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )
    reset_link = f"http://localhost:8000/reset_password?token={reset_token}"

    send_reset_email(user.email_id, reset_link)

    return {"message": "Password reset link has been sent to your email"}


app.include_router(login_router)