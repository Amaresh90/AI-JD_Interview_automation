from fastapi import APIRouter, HTTPException,Request,FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from loguru import logger
from database.schema import all_details, hr_details
from database.config import hr_collection, domain_collection, roles_collection
import re
from passlib.context import CryptContext
from datetime import datetime

hr_router = APIRouter()

logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO")

app = FastAPI()

@app.middleware("http")
async def error_logging_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.exception(f"Server Error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error occurred"}
        )


class User(BaseModel):
    full_name: str = Field(..., description="Full name of the HR")
    emp_id: str = Field(..., pattern=r'^DB\d+$', description="Must start with DB followed by digits")
    phone_no: str = Field(..., pattern=r"^(91\d{10}|0\d{10}|\d{10})$", description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX")
    email_id: EmailStr = Field(..., description="Valid email is required")
    password: str = Field(..., min_length=8, description="Password must include at least 1 uppercase, 1 lowercase, 1 digit, and 1 special character")
    role: str

    @field_validator("password")
    def validate_password(cls, v):
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("lowercase letter")
        if not re.search(r"\d", v):
            errors.append("digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("special character")
        if errors:
            raise ValueError(f"Password must contain at least one {', '.join(errors)}")
        return v

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Endpoints------
# 1.create user-------
@hr_router.post("/create_user")
def create_user(user: User):

    if hr_collection.find_one({"emp_id": user.emp_id}):
        raise HTTPException(status_code=400, detail="User with this ID already exists")

    email_domain = user.email_id.split('@')[-1]
    if not domain_collection.find_one({"domain": f"@{email_domain}"}):
        raise HTTPException(status_code=400, detail="Enter a valid email domain")

    if not roles_collection.find_one({"role": user.role}):
        raise HTTPException(status_code=400, detail="Enter a valid role")

    hashed_password = pwd_context.hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password  

    now = datetime.utcnow()
    user_data["created_at"] = now
    user_data["updated_at"] = None

    result = hr_collection.insert_one(user_data)
    return {
        "status_code": 201,
        "message": "User created successfully",
        "payload": hr_details(user_data),
    }

# delete user data
@hr_router.delete("/delete/{emp_id}")
def delete_user(emp_id: str):
    result = hr_collection.delete_one({"emp_id": emp_id})
    if result.deleted_count == 0:
        logger.error(f"Delete failed - user not found: {emp_id}")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User deleted: {emp_id}")
    return {
        "status_code": 200,
        "message": "User deleted successfully",
    }

# update user data
@hr_router.put("/update_user/{emp_id}")
def update_user(emp_id: str, user: User):
        existing_user = hr_collection.find_one({"emp_id": emp_id})
        if not existing_user:
            logger.error(f"Update failed - user not found: {emp_id}")
            raise HTTPException(status_code=404, detail="User not found")

        # Validate email domain
        email_domain = user.email_id.split('@')[-1]
        if not domain_collection.find_one({"domain": f"@{email_domain}"}):
            logger.error(f"Invalid email domain: {email_domain}")
            raise HTTPException(status_code=400, detail="Enter a valid email domain")

        # Validate role
        if not roles_collection.find_one({"role": user.role}):
            logger.error(f"Invalid role: {user.role}")
            raise HTTPException(status_code=400, detail="Enter a valid role")

        update_data = user.dict()
        update_data["updated_at"] = datetime.utcnow()

        hr_collection.update_one({"emp_id": emp_id}, {"$set": update_data})
        logger.info(f"User updated: {emp_id}")
        return {
            "status_code": 200,
            "message": "User updated successfully",
            "payload": hr_details(update_data),
        }

# get all users data
@hr_router.get("/")
def get_all_users():
        users = list(hr_collection.find())
        if not users:
            logger.info("No users found in HR collection.")
            return {
                "status_code": 200,
                "message": "No users found.",
                "payload": []
            }
        for user in users:
            user.pop('_id', None)
        logger.info(f"Fetched {len(users)} users.")
        return {
            "status_code": 200,
            "message": "Users fetched successfully",
            "payload": all_details(users),
        }

app.include_router(hr_router)
