from fastapi import APIRouter, HTTPException, FastAPI, Depends, Request
from pydantic import BaseModel, Field
from bson.objectid import ObjectId
from database.config import domain_collection
from database.schema import domain_details, all_domain_details
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional
from datetime import datetime

# --- router----
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
        request.state.user = payload
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return await call_next(request)

# Dependency for role check
def super_admin_required(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    role = payload.get("role", "").lower()
    if role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="Only super_admin can perform this action")
    return payload

# ---base models---
class Domain(BaseModel):
    domain: str = Field(..., pattern=r'^@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$',
    description="The domain should be a valid domain like example.com"
    )
    active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None  

class DomainUpdate(BaseModel):
    domain_id: str
    new_domain: str

class DomainDelete(BaseModel):
    domain_id: str 

#----- validation handler -----
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()

    missing_fields = [err["loc"][-1] for err in errors if err.get("type") == "value_error.missing"]
    invalid_fields = [
        {"field": err["loc"][-1], "message": err.get("msg")}
        for err in errors if err.get("type") != "value_error.missing"
    ]

    response_content = {}
    if missing_fields:
        response_content["missing_fields"] = missing_fields
    if invalid_fields:
        response_content["invalid_fields"] = invalid_fields

    return JSONResponse(status_code=422, content=response_content)


# ----------------------------
@domain_router.post("/create_domain", dependencies=[Depends(super_admin_required)])
def create_domain(domain: Domain):
    # try:
        if not domain.active:
            raise HTTPException(status_code=400, detail="Domain must be active to create")

        now = datetime.utcnow()
        domain_data = {
            "domain": domain.domain,
            "active": domain.active,
            "created_at": now,
            "updated_at": now
        }

        new_domain_id = domain_collection.insert_one(domain_data).inserted_id
        new_domain = domain_collection.find_one({"_id": new_domain_id})

        return {
            "status_code": 201,
            "message": "Domain created successfully",
            "domain": domain_details(new_domain)
        }
    # except Exception as e:
    #     return {
    #         "message": f"Internal Server Error: {str(e)}",
    #         "status_code": 500
    #     }


@domain_router.get("/get_domain", dependencies=[Depends(super_admin_required)])
def get_domain():
    domains = list(domain_collection.find())
    return {
        "status_code": 200,
        "message": "success",
        "payload": all_domain_details(domains)
    }

@domain_router.put("/update", dependencies=[Depends(super_admin_required)])
async def update_domain(input_data: DomainUpdate):
    
    if not ObjectId.is_valid(input_data.domain_id):
        raise HTTPException(status_code=400, detail="Invalid domain ID")

    if domain_collection.find_one({"domain": input_data.new_domain}):
        raise HTTPException(status_code=409, detail="Domain name already exists")

    updated = domain_collection.update_one(
        {"_id": ObjectId(input_data.domain_id)},
        {"$set": {"domain": input_data.new_domain, "updated_at": datetime.utcnow()}}
    )

    if updated.matched_count == 0:
        raise HTTPException(status_code=404, detail="Domain not found")

    return {"status_code": 200, "message": "Domain updated successfully"}


# -------------------- Delete Domain --------------------
@domain_router.delete("/delete", dependencies=[Depends(super_admin_required)])
async def delete_domain(input_data: DomainDelete):

    if not ObjectId.is_valid(input_data.domain_id):
        raise HTTPException(status_code=400, detail="Invalid domain ID")

    deleted = domain_collection.delete_one({"_id": ObjectId(input_data.domain_id)})
    if deleted.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Domain not found")
    return {"status_code": 200, "message": "Domain deleted successfully"}

# include router
app.include_router(domain_router)
