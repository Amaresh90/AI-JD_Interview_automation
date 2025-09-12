from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from bson.objectid import ObjectId
from database.config import domain_collection
from database.schema import domain_details, all_domain_details
from jose import jwt, JWTError
import logging
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from datetime import datetime
from typing import List

# logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",

)
logger = logging.getLogger("__name__")
logger.setLevel(logging.INFO)

domain_router = APIRouter()
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
    if role not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Only super_admin or admin can view this page")
    return payload
# ----------------- Pydantic Model ----------------
class domains(BaseModel):
    domain: str = Field(..., min_length=2, max_length=20,  pattern=r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$',description="The domain should be a valid domain like example.com")
    is_active: bool | None = None 
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class domainUpdateRequest(BaseModel):
    domain_id: str
    new_domain: str
    is_active: bool | None = None 

class domainDeleteRequest(BaseModel):
    domain_id: List[str]


# create (only super_admin)

@domain_router.post("/", dependencies=[Depends(super_admin_required)])
async def create_domain(input_data: domains):
    logger.info(f"Attempting to create domain: {input_data.domain}, is_active={input_data.is_active}")

    if domain_collection.find_one({"domain": input_data.domain}):
        logger.error(f"domain '{input_data.domain}' already exists")
        raise HTTPException(status_code=409, detail="domain already exists")  

    now = datetime.utcnow()
    domain_data = {
        "domain": input_data.domain,
        "is_active": input_data.is_active,
        "created_at": now,
        "updated_at": now
    }

    new_domain_id = domain_collection.insert_one(domain_data).inserted_id
    logger.info(f"domain created successfully with ID: {new_domain_id}")

    return {
        "status_code": 201,
        "message": "domain added",
        "domain": domain_details(domain_collection.find_one({"_id": new_domain_id}))
        # "playload": domain_data
    }


# ------------------- domain page --------------------
def domain_details(domain: dict) -> dict:
    return {
        "id": str(domain.get("_id")),         
        "domain": domain.get("domain", ""),         
        "is_active": domain.get("is_active", False)  
    }


def all_domain_details(domains) -> list:
    return [domain_details(domain) for domain in domains]


# get all domains (any logged-in user can view)
@domain_router.get("/")
async def get_domains():
    logger.info("Fetching all domains")
    try:
        domains = all_domain_details(domain_collection.find())
        return {"status_code": 200, "domains": domains}
    except Exception as e:
        logger.error(f"Error while fetching domains: {e}")
        return {"status_code": 500, "message": "Internal Server Error"}



@domain_router.put("/", dependencies=[Depends(super_admin_required)])
async def update_domain(input_data: domainUpdateRequest):
    logger.info(f"=======>")
    logger.info(f"Attempting to update domain ID: {input_data.domain_id}, is_active = {input_data.is_active}")

    if not ObjectId.is_valid(input_data.domain_id):
        logger.error("Invalid domain ID format")
        raise HTTPException(status_code=400, detail="Invalid domain ID")

    # Prevent duplicate domain names except for the current domain
    existing = domain_collection.find_one({
        "domain": input_data.new_domain,
        "_id": {"$ne": ObjectId(input_data.domain_id)}
    })
    if existing:
        logger.error(f"domain '{input_data.new_domain}' already exists")
        raise HTTPException(status_code=409, detail="domain name already exists")

    updated = domain_collection.update_one(
        {"_id": ObjectId(input_data.domain_id)},
        {"$set": {
            "domain": input_data.new_domain,
            "is_active": input_data.is_active,
            "updated_at": datetime.utcnow()
        }}
    )

    if updated.matched_count == 0:
        logger.warning(f"No domain found with ID: {input_data.domain_id}")
        raise HTTPException(status_code=404, detail="domain not found")

    logger.info(f"domain ID {input_data.domain_id} updated successfully")
    return {"status_code": 200, "message": "domain updated successfully"}

# delete (only super_admin)

# delete multiple domains (only super_admin)
@domain_router.delete("/", dependencies=[Depends(super_admin_required)])
async def delete_domains(input_data: domainDeleteRequest):
    logger.info(f"Attempting to delete domain IDs: {input_data.domain_id}")

    # Validate domain_ids is a list
    if not isinstance(input_data.domain_id, list) or not input_data.domain_id:
        raise HTTPException(status_code=400, detail="domain_ids must be a non-empty list")

    # Validate all IDs
    valid_ids = []
    for domain_id in input_data.domain_id:
        if ObjectId.is_valid(domain_id):
            valid_ids.append(ObjectId(domain_id))
        else:
            logger.warning(f"Invalid domain ID skipped: {domain_id}")

    if not valid_ids:
        raise HTTPException(status_code=400, detail="No valid domain IDs provided")

    # Delete multiple domains
    result = domain_collection.delete_many({"_id": {"$in": valid_ids}})

    if result.deleted_count == 0:
        logger.warning("No domains found for deletion")
        raise HTTPException(status_code=404, detail="No domains found")

    logger.info(f"Deleted {result.deleted_count} domain(s) successfully")
    return {
        "status_code": 200,
        "message": f"{result.deleted_count} domain(s) deleted successfully"
    }



app.include_router(domain_router)
