# # from fastapi import APIRouter, HTTPException,Request,FastAPI
# # from fastapi.responses import JSONResponse
# # from pydantic import BaseModel, EmailStr, Field, field_validator
# # from loguru import logger
# # from database.schema import all_details, hr_details
# # from database.config import hr_collection, domain_collection, roles_collection
# # import re
# # from passlib.context import CryptContext
# # from datetime import datetime

# # hr_router = APIRouter()

# # logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO")

# # app = FastAPI()

# # @app.middleware("http")
# # async def error_logging_middleware(request: Request, call_next):
# #     try:
# #         response = await call_next(request)
# #         return response
# #     except Exception as e:
# #         logger.exception(f"Server Error: {e}")
# #         return JSONResponse(
# #             status_code=500,
# #             content={"error": "Internal server error occurred"}
# #         )


# # class User(BaseModel):
# #     full_name: str = Field(..., description="Full name of the HR")
# #     emp_id: str = Field(..., pattern=r'^DB\d+$', description="Must start with DB followed by digits")
# #     phone_no: str = Field(..., pattern=r"^(91\d{10}|0\d{10}|\d{10})$", description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX")
# #     email_id: EmailStr = Field(..., description="Valid email is required")
# #     password: str = Field(..., min_length=8, description="Password must include at least 1 uppercase, 1 lowercase, 1 digit, and 1 special character")
# #     role: str

# #     @field_validator("password")
# #     def validate_password(cls, v):
# #         errors = []
# #         if not re.search(r"[A-Z]", v):
# #             errors.append("uppercase letter")
# #         if not re.search(r"[a-z]", v):
# #             errors.append("lowercase letter")
# #         if not re.search(r"\d", v):
# #             errors.append("digit")
# #         if not re.search(r"[^A-Za-z0-9]", v):
# #             errors.append("special character")
# #         if errors:
# #             raise ValueError(f"Password must contain at least one {', '.join(errors)}")
# #         return v

# # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # # Endpoints------
# # # 1.create user-------
# # @hr_router.post("/create_user")
# # def create_user(user: User):

# #     if hr_collection.find_one({"emp_id": user.emp_id}):
# #         raise HTTPException(status_code=400, detail="User with this ID already exists")

# #     email_domain = user.email_id.split('@')[-1]
# #     if not domain_collection.find_one({"domain": f"@{email_domain}"}):
# #         raise HTTPException(status_code=400, detail="Enter a valid email domain")

# #     if not roles_collection.find_one({"role": user.role}):
# #         raise HTTPException(status_code=400, detail="Enter a valid role")

# #     hashed_password = pwd_context.hash(user.password)
# #     user_data = user.dict()
# #     user_data["password"] = hashed_password  

# #     now = datetime.utcnow()
# #     user_data["created_at"] = now
# #     user_data["updated_at"] = None

# #     result = hr_collection.insert_one(user_data)
# #     return {
# #         "status_code": 201,
# #         "message": "User created successfully",
# #         "payload": hr_details(user_data),
# #     }

# # # delete user data
# # @hr_router.delete("/delete/{emp_id}")
# # def delete_user(emp_id: str):
# #     result = hr_collection.delete_one({"emp_id": emp_id})
# #     if result.deleted_count == 0:
# #         logger.error(f"Delete failed - user not found: {emp_id}")
# #         raise HTTPException(status_code=404, detail="User not found")

# #     logger.info(f"User deleted: {emp_id}")
# #     return {
# #         "status_code": 200,
# #         "message": "User deleted successfully",
# #     }

# # # update user data
# # @hr_router.put("/update_user/{emp_id}")
# # def update_user(emp_id: str, user: User):
# #         existing_user = hr_collection.find_one({"emp_id": emp_id})
# #         if not existing_user:
# #             logger.error(f"Update failed - user not found: {emp_id}")
# #             raise HTTPException(status_code=404, detail="User not found")

# #         # Validate email domain
# #         email_domain = user.email_id.split('@')[-1]
# #         if not domain_collection.find_one({"domain": f"@{email_domain}"}):
# #             logger.error(f"Invalid email domain: {email_domain}")
# #             raise HTTPException(status_code=400, detail="Enter a valid email domain")

# #         # Validate role
# #         if not roles_collection.find_one({"role": user.role}):
# #             logger.error(f"Invalid role: {user.role}")
# #             raise HTTPException(status_code=400, detail="Enter a valid role")

# #         update_data = user.dict()
# #         update_data["updated_at"] = datetime.utcnow()

# #         hr_collection.update_one({"emp_id": emp_id}, {"$set": update_data})
# #         logger.info(f"User updated: {emp_id}")
# #         return {
# #             "status_code": 200,
# #             "message": "User updated successfully",
# #             "payload": hr_details(update_data),
# #         }

# # # get all users data
# # @hr_router.get("/")
# # def get_all_users():
# #         users = list(hr_collection.find())
# #         if not users:
# #             logger.info("No users found in HR collection.")
# #             return {
# #                 "status_code": 200,
# #                 "message": "No users found.",
# #                 "payload": []
# #             }
# #         for user in users:
# #             user.pop('_id', None)
# #         logger.info(f"Fetched {len(users)} users.")
# #         return {
# #             "status_code": 200,
# #             "message": "Users fetched successfully",
# #             "payload": all_details(users),
# #         }

# # app.include_router(hr_router)

# from fastapi import APIRouter, HTTPException, Request, FastAPI
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel, EmailStr, Field, field_validator
# from loguru import logger
# from database.schema import all_details, hr_details
# from database.config import hr_collection, domain_collection, roles_collection
# import re
# from passlib.context import CryptContext
# from datetime import datetime
# from typing import List, Optional
# from bson import ObjectId

# hr_router = APIRouter()

# logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO")

# app = FastAPI()

# @app.middleware("http")
# async def error_logging_middleware(request: Request, call_next):
#     try:
#         response = await call_next(request)
#         return response
#     except Exception as e:
#         logger.exception(f"Server Error: {e}")
#         return JSONResponse(
#             status_code=500,
#             content={"error": "Internal server error occurred"}
#         )

# # ---------------------------
# # MODELS
# # ---------------------------
# class User(BaseModel):
#     user_id: str
#     full_name: str = Field(..., description="Full name of the HR")
#     emp_id: str = Field(..., pattern=r'^DB\d+$', description="Must start with DB followed by digits")
#     phone_no: str = Field(..., pattern=r"^(91\d{10}|0\d{10}|\d{10})$", description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX")
#     email_id: EmailStr = Field(..., description="Valid email is required")
#     password: str = Field(..., min_length=8, description="Password must include at least 1 uppercase, 1 lowercase, 1 digit, and 1 special character")
#     role: str
#     is_active: bool = Field(default=True, description="Whether the user is active or not")

# # ---------------------------
# class UpdateUserRequest(BaseModel):
#     user_id: str
#     full_name: Optional[str] = None
#     emp_id: Optional[str] = Field(None, pattern=r'^DB\d+$')
#     phone_no: Optional[str] = Field(
#         None,
#         pattern=r"^(91\d{10}|0\d{10}|\d{10})$",
#         description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX"
#     )
#     email_id: Optional[EmailStr] = None
#     password: Optional[str] = Field(None, min_length=8)
#     role: Optional[str] = None
#     is_active: Optional[bool] = None
#     @field_validator("password")
#     def validate_password(cls, v):
#         errors = []
#         if not re.search(r"[A-Z]", v):
#             errors.append("uppercase letter")
#         if not re.search(r"[a-z]", v):
#             errors.append("lowercase letter")
#         if not re.search(r"\d", v):
#             errors.append("digit")
#         if not re.search(r"[^A-Za-z0-9]", v):
#             errors.append("special character")
#         if errors:
#             raise ValueError(f"Password must contain at least one {', '.join(errors)}")
#         return v


# class DeleteUsersRequest(BaseModel):
#     emp_id: List[str] = Field(..., description="List of employee IDs to delete")


# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # ---------------------------
# # ENDPOINTS
# # ---------------------------

# # 1. create user
# @hr_router.post("/create_user")
# def create_user(user: User):
#     if hr_collection.find_one({"emp_id": user.emp_id}):
#         raise HTTPException(status_code=400, detail="User with this ID already exists")

#     email_domain = user.email_id.split('@')[-1]
#     if not domain_collection.find_one({"domain":email_domain}):
#         raise HTTPException(status_code=400, detail="Enter a valid email domain")

#     if not roles_collection.find_one({"role": user.role}):
#         raise HTTPException(status_code=400, detail="Enter a valid role")

#     hashed_password = pwd_context.hash(user.password)
#     user_data = user.dict()
#     user_data["password"] = hashed_password  

#     now = datetime.utcnow()
#     user_data["created_at"] = now
#     user_data["updated_at"] = None

#     hr_collection.insert_one(user_data)
#     return {
#         "status_code": 201,
#         "message": "User created successfully",
#         "payload": hr_details(user_data),
#     }

# # 2. delete multiple users
# @hr_router.delete("/delete")
# def delete_users(request: DeleteUsersRequest):
#     result = hr_collection.delete_many({"emp_id": {"$in": request.emp_id}})
#     if result.deleted_count == 0:
#         logger.error(f"Delete failed - no users found: {request.emp_id}")
#         raise HTTPException(status_code=404, detail="No users found to delete")

#     logger.info(f"Deleted {result.deleted_count} users: {request.emp_id}")
#     return {
#         "status_code": 200,
#         "message": f"{result.deleted_count} users deleted successfully",
#     }
# # 3. Update full user details

# @hr_router.put("/update_user")
# def update_user(request: UpdateUserRequest):
#     try:
#         object_id = ObjectId(request.user_id)
#     except Exception:
#         logger.error(f"Invalid ObjectId: {request.user_id}")
#         raise HTTPException(status_code=400, detail="Invalid user_id format")

#     # Find by _id
#     existing_user = hr_collection.find_one({"_id": object_id})
#     if not existing_user:
#         logger.error(f"Update failed - user not found: {request.user_id}")
#         raise HTTPException(status_code=404, detail="User not found")

#     update_data = request.dict(exclude_unset=True, exclude={"user_id"})
#     update_data["updated_at"] = datetime.utcnow()

#     # Validate email domain if provided
#     if "email_id" in update_data:
#         email_domain = update_data["email_id"].split('@')[-1]
#         if not domain_collection.find_one({"domain": email_domain}):
#             logger.error(f"Invalid email domain: {email_domain}")
#             raise HTTPException(status_code=400, detail="Enter a valid email domain")

#     # Validate role if provided
#     if "role" in update_data:
#         if not roles_collection.find_one({"role": update_data["role"]}):
#             logger.error(f"Invalid role: {update_data['role']}")
#             raise HTTPException(status_code=400, detail="Enter a valid role")

#     # Hash password if updated
#     if "password" in update_data:
#         update_data["password"] = pwd_context.hash(update_data["password"])

#     hr_collection.update_one({"_id": object_id}, {"$set": update_data})
#     updated_user = hr_collection.find_one({"_id": object_id})

#     updated_user["_id"] = str(updated_user["_id"])

#     logger.info(f"User updated: {request.user_id}")
#     return {
#         "status_code": 200,
#         "message": "User updated successfully",
#         "payload": updated_user
#     }


# @hr_router.get("/")
# def get_all_users():
#     users = list(hr_collection.find())
#     if not users:
#         return {"status_code": 200, "message": "No users found.", "payload": []}

#     # Do not pop _id, let hr_details handle it
#     return {
#         "status_code": 200,
#         "message": "Users fetched successfully",
#         "payload": all_details(users),
#     }


# app.include_router(hr_router)

from fastapi import APIRouter, HTTPException, Request, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from loguru import logger
from database.config import hr_collection, domain_collection, roles_collection
import re
from passlib.context import CryptContext
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import Body

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

# ---------------------------
# MODELS
# ---------------------------

# Creation model (no user_id required)
class UserCreate(BaseModel):
    full_name: str = Field(..., description="Full name of the HR")
    emp_id: str = Field(..., pattern=r'^DB\d+$', description="Must start with DB followed by digits")
    phone_no: str = Field(..., pattern=r"^(91\d{10}|0\d{10}|\d{10})$", description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX")
    email_id: EmailStr = Field(..., description="Valid email is required")
    password: str = Field(..., min_length=8, description="Password must include at least 1 uppercase, 1 lowercase, 1 digit, and 1 special character")
    role: str
    is_active: bool = Field( description="Whether the user is active or not")

# Update model
class UpdateUserRequest(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    emp_id: Optional[str] = Field(None, pattern=r'^DB\d+$')
    phone_no: Optional[str] = Field(
        None,
        pattern=r"^(91\d{10}|0\d{10}|\d{10})$",
        description="Phone number should be in format: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX"
    )
    email_id: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = None
    is_active: Optional[bool] = None

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

# Delete model
class DeleteUsersRequest(BaseModel):
    emp_id: List[str] = Field(..., description="List of employee IDs to delete")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------
# UTILITIES
# ---------------------------
def hr_details(hr):
    return {
        "id": str(hr["_id"]),
        "full_name": hr.get("full_name"),
        "emp_id": hr.get("emp_id"),
        "phone_no": hr.get("phone_no"),
        "email_id": hr.get("email_id"),
        "password": hr.get("password"),
        "role": hr.get("role"),
        "is_active": hr.get("is_active"),
    }

def all_details(hrs):
    return [hr_details(hr) for hr in hrs]

# ---------------------------
# ENDPOINTS
# ---------------------------

# 1. Create user
@hr_router.post("/create_user")
def create_user(user: UserCreate):
    if hr_collection.find_one({"emp_id": user.emp_id}):
        raise HTTPException(status_code=400, detail="User with this ID already exists")

    email_domain = user.email_id.split('@')[-1]
    if not domain_collection.find_one({"domain": email_domain}):
        raise HTTPException(status_code=400, detail="Enter a valid email domain")

    if not roles_collection.find_one({"role": user.role}):
        raise HTTPException(status_code=400, detail="Enter a valid role")

    hashed_password = pwd_context.hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = None

    inserted = hr_collection.insert_one(user_data)
    user_data["_id"] = str(inserted.inserted_id)  # Convert ObjectId to string

    return {
        "status_code": 201,
        "message": "User created successfully",
        "payload": hr_details(user_data),
    }

# # 2. Delete multiple users
@hr_router.delete("/delete")
def delete_users(request: DeleteUsersRequest = Body(...)):
    result = hr_collection.delete_many({"emp_id": {"$in": request.emp_id}})
    if result.deleted_count == 0:
        logger.error(f"Delete failed - no users found: {request.emp_id}")
        raise HTTPException(status_code=404, detail="No users found to delete")

    logger.info(f"Deleted {result.deleted_count} users: {request.emp_id}")
    return {
        "status_code": 200,
        "message": f"{result.deleted_count} users deleted successfully",
    }

# @hr_router.delete("/delete/{emp_id}")
# def delete_user(emp_id: str):
#     result = hr_collection.delete_one({"emp_id": emp_id})
#     if result.deleted_count == 0:
#         logger.error(f"Delete failed - user not found: {emp_id}")
#         raise HTTPException(status_code=404, detail="User not found")

#     logger.info(f"User deleted: {emp_id}")
#     return {"status_code": 200, "message": "User deleted successfully"}


# 3. Update full user details
@hr_router.put("/update_user")
def update_user(request: UpdateUserRequest):
    try:
        object_id = ObjectId(request.user_id)
    except Exception:
        logger.error(f"Invalid ObjectId: {request.user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    existing_user = hr_collection.find_one({"_id": object_id})
    if not existing_user:
        logger.error(f"Update failed - user not found: {request.user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    update_data = request.dict(exclude_unset=True, exclude={"user_id"})
    update_data["updated_at"] = datetime.utcnow()

    if "email_id" in update_data:
        email_domain = update_data["email_id"].split('@')[-1]
        if not domain_collection.find_one({"domain": email_domain}):
            logger.error(f"Invalid email domain: {email_domain}")
            raise HTTPException(status_code=400, detail="Enter a valid email domain")

    if "role" in update_data:
        if not roles_collection.find_one({"role": update_data["role"]}):
            logger.error(f"Invalid role: {update_data['role']}")
            raise HTTPException(status_code=400, detail="Enter a valid role")

    if "password" in update_data:
        update_data["password"] = pwd_context.hash(update_data["password"])

    hr_collection.update_one({"_id": object_id}, {"$set": update_data})
    updated_user = hr_collection.find_one({"_id": object_id})
    updated_user["_id"] = str(updated_user["_id"])

    logger.info(f"User updated: {request.user_id}")
    return {
        "status_code": 200,
        "message": "User updated successfully",
        "payload": updated_user
    }

# 4. Get all users

@hr_router.get("/")
def get_all_users():
    users = list(hr_collection.find())
    for u in users:
        u["_id"] = str(u["_id"])  # convert to string
    return {
        "status_code": 200,
        "message": "Users fetched successfully",
        "payload": users,
    }

# ---------------------------
app.include_router(hr_router)
