from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from bson.objectid import ObjectId
from database.config import roles_collection
from database.schema import role_details, all_role_details
from jose import jwt, JWTError
import logging
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from datetime import datetime

# logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

role_router = APIRouter()
app = FastAPI()

# ---------------- TOKEN CONFIG ----------------
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Decode & validate token
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Middleware for authentication
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = ["/login", "/openapi.json", "/docs", "/redoc"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization header missing or invalid"})

    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
        request.state.user = payload  # save user payload in request
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return await call_next(request)


# # Dependency for role check
def super_admin_required(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    role = payload.get("role", "").lower()
    if role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="Only super_admin can view this page")
    return payload

# ----------------- Pydantic Model ----------------
class Roles(BaseModel):
    role: str = Field(..., min_length=2, max_length=20, pattern="^[A-Za-z_ ]+$", description="The role should be a unique name")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RoleUpdateRequest(BaseModel):
    role_id: str
    new_role: str

class RoleDeleteRequest(BaseModel):
    role_id: str


# create (only super_admin)

@role_router.post("/", dependencies=[Depends(super_admin_required)])
async def create_role(input_data: Roles):
    logger.info(f"Attempting to create role: {input_data.role}")

    if roles_collection.find_one({"role": input_data.role}):
        logger.error(f"Role '{input_data.role}' already exists")
        raise HTTPException(status_code=409, detail="Role already exists")  

    now = datetime.utcnow()
    role_data = {
        "role": input_data.role,
        "created_at": now,
        "updated_at": now
    }

    new_role_id = roles_collection.insert_one(role_data).inserted_id
    logger.info(f"Role created successfully with ID: {new_role_id}")

    return {
        "status_code": 201,
        "message": "Role added",
        "Role": role_details(roles_collection.find_one({"_id": new_role_id}))
    }


# get all roles (any logged-in user can view)
@role_router.get("/")
async def get_roles():
    logger.info("Fetching all roles")
    roles = all_role_details(roles_collection.find())
    return {"status_code": 200, "roles": roles}



# update (only super_admin)
@role_router.put("/", dependencies=[Depends(super_admin_required)])
async def update_role(input_data: RoleUpdateRequest):
    logger.info(f"Attempting to update role ID: {input_data.role_id}")

    if not ObjectId.is_valid(input_data.role_id):
        logger.error("Invalid role ID format")
        raise HTTPException(status_code=400, detail="Invalid role ID")

    if roles_collection.find_one({"role": input_data.new_role}):
        logger.error(f"Role '{input_data.new_role}' already exists")
        raise HTTPException(status_code=409, detail="Role name already exists")

    updated = roles_collection.update_one(
        {"_id": ObjectId(input_data.role_id)},
        {"$set": {"role": input_data.new_role, "updated_at": datetime.utcnow()}}
    )

    if updated.matched_count == 0:
        logger.warning(f"No role found with ID: {input_data.role_id}")
        raise HTTPException(status_code=404, detail="Role not found")

    logger.info(f"Role ID {input_data.role_id} updated successfully")
    return {"status_code": 200, "message": "Role updated successfully"}


# delete (only super_admin)
@role_router.delete("/", dependencies=[Depends(super_admin_required)])
async def delete_role(input_data: RoleDeleteRequest):
    logger.info(f"Attempting to delete role ID: {input_data.role_id}")
    if not ObjectId.is_valid(input_data.role_id):
        logger.error("Invalid role ID format")
        raise HTTPException(status_code=400, detail="Invalid role ID")

    deleted = roles_collection.delete_one({"_id": ObjectId(input_data.role_id)})
    if deleted.deleted_count == 0:
        logger.warning(f"No role found with ID: {input_data.role_id}")
        raise HTTPException(status_code=404, detail="Role not found")

    logger.info(f"Role ID {input_data.role_id} deleted successfully")
    return {"status_code": 200, "message": "Role deleted successfully"}



app.include_router(role_router)
