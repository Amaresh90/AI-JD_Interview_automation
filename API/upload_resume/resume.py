from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter,Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import fitz  
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from AI.env import ENVS_KEYS
from fastapi import Path
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi.responses import FileResponse
from typing import List
from database.config import resume_collection
from bson.objectid import ObjectId


# ------------------- APP -------------------
app = FastAPI()
resume_router = APIRouter()


UPLOAD_DIR = "uploaded_resumes"


SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RESET_TOKEN_EXPIRE_MINUTES = 10  

# ---------------------------------
class Update_resume(BaseModel):
    is_active: bool | None = None 

class FolderUpdateItem(BaseModel):
    old_folder: str
    new_folder: str

class FolderUpdateRequest(BaseModel):
    updates: List[FolderUpdateItem]

class FolderDeleteRequest(BaseModel):
    folders: List[str]

class FileDeleteRequest(BaseModel):
    file: List[str]
    

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


# # Dependency for role check
def required(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    role = payload.get("role", "").lower()
    if role not in ["super_admin","hr"]:
        raise HTTPException(status_code=403, detail="Only super_admin or HR can view this page")
    return payload

# ------------------- LLM FUNCTION -------------------
def extract_resume_data(text: str) -> dict:
  
    prompt = f"""
    Extract the following details from the resume:
    - Full Name
    - Email
    - Phone Number
    - Location

    Return ONLY the JSON in format: {{ "name": "", "email": "", "phone": "", "location": "" }}
    Resume Text:
    {text}
    """

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set in environment")

    chat = ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model="gemini-2.0-flash",
        temperature=0
    )

    try:
        response = chat.invoke([{"role": "user", "content": prompt}])
        content = getattr(response, "content", None)
        print("LLM raw output:", content)

        if not content:
            raise HTTPException(status_code=500, detail="No content returned from LLM")

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise HTTPException(status_code=500, detail=f"Invalid JSON from LLM: {content}")
        content = content[start:end+1].replace("'", '"')

        data = json.loads(content)
        for key in ["name", "email", "phone", "location"]:
            if key not in data:
                data[key] = None

    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {content}")

    return data


# ------------------- HELPERS -------------------
def save_pdf(file: UploadFile) -> str:
    """
    Save uploaded PDF into a date-based folder.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    save_path = os.path.join(UPLOAD_DIR, today)
    os.makedirs(save_path, exist_ok=True)

    file_path = os.path.join(save_path, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract plain text from PDF using PyMuPDF.
    """
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()
    return text


# # ------------------- ENDPOINT -------------------
# 1) upload resume
@resume_router.post("/upload_resume",dependencies=[Depends(required)])
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        file_path = save_pdf(file)
        text = extract_text_from_pdf(file_path)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to process PDF")

    try:
        extracted_data = await run_in_threadpool(extract_resume_data, text)
    except Exception as e:
        print(f"Error from LLM: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract resume data")
    today = datetime.now().strftime("%Y-%m-%d")

    record = {
            "name": extracted_data.get("name"),
            "email": extracted_data.get("email"),
            "phone": extracted_data.get("phone"),
            "location": extracted_data.get("location"),
            "file_name": f"{today}/{file.filename}",
            "is_selected": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "text": text,
        }
    try:
        resume_collection.insert_one(record)
    except Exception as e:
        print(f"Error saving to DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to save resume data")

    response_data = extracted_data.copy()
    response_data["is_selected"] = False

    return JSONResponse(content=response_data)
  

# 3.list of folders
@resume_router.get("/list_folders",dependencies=[Depends(required)])
async def list_folders():
    if not os.path.exists(UPLOAD_DIR):
        return {"message": "folder does not exist" }

    folders = [f for f in os.listdir(UPLOAD_DIR) if os.path.isdir(os.path.join(UPLOAD_DIR, f))]
    folders.sort(reverse=True)  
    return {"folders": folders}


# 3) upload folder
@resume_router.put("/update_folder", dependencies=[Depends(required)])
async def update_folders(request: FolderUpdateRequest):
    results = []

    for item in request.updates:
        old_path = os.path.join(UPLOAD_DIR, item.old_folder)
        new_path = os.path.join(UPLOAD_DIR, item.new_folder)

        if not os.path.exists(old_path):
            results.append({
                "old_folder": item.old_folder,
                "new_folder": item.new_folder,
                "status": "failed",
                "message": f"Folder '{item.old_folder}' does not exist"
            })
            continue

        if os.path.exists(new_path):
            results.append({
                "old_folder": item.old_folder,
                "new_folder": item.new_folder,
                "status": "failed",
                "message": f"Folder '{item.new_folder}' already exists"
            })
            continue

        try:
            os.rename(old_path, new_path)
            results.append({
                "old_folder": item.old_folder,
                "new_folder": item.new_folder,
                "status": "success",
                "message": f"Folder '{item.old_folder}' renamed to '{item.new_folder}'"
            })
        except Exception as e:
            results.append({
                "old_folder": item.old_folder,
                "new_folder": item.new_folder,
                "status": "error",
                "message": str(e)
            })

    return {"results": results}


@resume_router.delete("/delete_folder", dependencies=[Depends(required)])
async def delete_folders(request: FolderDeleteRequest):
    results = []

    for folder_name in request.folders:
        folder_path = os.path.join(UPLOAD_DIR, folder_name)

        if not os.path.exists(folder_path):
            results.append({
                "folder": folder_name,
                "status": "failed",
                "message": f"Folder '{folder_name}' does not exist"
            })
            continue

        try:
            os.rmdir(folder_path)  
            results.append({
                "folder": folder_name,
                "status": "success",
                "message": f"Folder '{folder_name}' deleted successfully"
            })
        except OSError:
            results.append({
                "folder": folder_name,
                "status": "failed",
                "message": f"Folder '{folder_name}' is not empty, cannot delete"
            })
        except Exception as e:
            results.append({
                "folder": folder_name,
                "status": "error",
                "message": str(e)
            })

    return {"results": results}
 

@resume_router.get("/list_files/{subfolder}",dependencies=[Depends(required)])
async def list_files(subfolder: str = Path(..., description="Subfolder name (date) inside uploaded_resumes")):
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise HTTPException(status_code=404, detail=f"Folder '{subfolder}' not found")

    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    files.sort()
    return {"files": files}


@resume_router.delete("/delete_file", dependencies=[Depends(required)])
async def delete_file(request: FileDeleteRequest):
    results = []

    for file_name in request.file:
        file_path = os.path.join(UPLOAD_DIR, file_name)

        if not os.path.exists(file_path):
            results.append({
                "file": file_name,
                "status": "failed",
                "message": f"File '{file_name}' does not exist"
            })
            continue

        try:
            os.rmdir(file_path)  
            results.append({
                "file": file_name,
                "status": "success",
                "message": f"File '{file_name}' deleted successfully"
            })
        except OSError:
            results.append({
                "file": file_name,
                "status": "failed",
                "message": f"File '{file_name}' is not empty, cannot delete"
            })
        except Exception as e:
            results.append({
                "file": file_name,
                "status": "error",
                "message": str(e)
            })

    return {"results": results}

@resume_router.get("/view_resume/{folder}/{filename}", dependencies=[Depends(required)])
async def view_resume(folder: str, filename: str):

    file_path = os.path.join(UPLOAD_DIR, folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )

app.include_router(resume_router)

