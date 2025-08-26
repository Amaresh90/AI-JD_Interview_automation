from fastapi import FastAPI, HTTPException, APIRouter, Request,Depends
import uuid
import os
from PyPDF2 import PdfReader 
from typing import Dict
from AI.match_backend import match_graph, MatchState 
from database.config import jd_collection, match_collection,resume_collection,qa_collection
import uuid
import os
from PyPDF2 import PdfReader 
from typing import Dict
from AI.match_backend import match_graph, MatchState 
from bson import ObjectId
from AI.match_backend import generate_qa_node
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi.responses import JSONResponse



# ------------------ FastAPI Setup ------------------

app = FastAPI()
match_router = APIRouter()

class GenerateQARequest(BaseModel):
    jd_id: str
    resume_id: str
    num_questions: int
    difficulty_level: str
    question_type: str 

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

 # ------------------ Helpers ------------------


def get_jds_by_ids(jd_ids: list):
    """Fetch only selected JDs by IDs"""
    results = jd_collection.find(
        {"_id": {"$in": jd_ids}, "is_active": True},
        projection={
            "_id": 1,
            "job_title": 1,
            "location": 1,
            "job_type": 1,
            "work_mode": 1,
            "experience_required": 1,
            "skills": 1,
            "job_summary": 1,
            "responsibilities": 1
        }
    )
    formatted = []
    for doc in results:
        doc["_id"] = str(doc["_id"])
        if isinstance(doc.get("skills"), dict):
            doc["skills"] = list(doc["skills"].values())
        if isinstance(doc.get("responsibilities"), dict):
            doc["responsibilities"] = list(doc["responsibilities"].values())
        formatted.append(doc)
    return formatted


def get_resumes():
    def extract_pdf_text(file_path):
        try:
            reader = PdfReader(file_path)
            return "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return f"Error reading PDF: {e}"

    base_dir = os.path.join(os.path.dirname(__file__), '../uploaded_resumes')
    all_files = []

    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            file_path = os.path.join(root, fname)
            if fname.lower().endswith('.pdf'):
                text = extract_pdf_text(file_path)
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception as e:
                    text = f"Error reading file: {e}"

            existing = resume_collection.find_one({"file_name": fname})
            if existing:
                resume_id = str(existing["_id"])
            else:
                result = resume_collection.insert_one({
                    "file_name": fname,
                    "text": text
                })
                resume_id = str(result.inserted_id)

            all_files.append({
                "resume_id": resume_id,
                "file_name": fname,
                "text": text
            })

    return all_files


def convert_objectid(obj):
    """Recursively convert ObjectId to str inside dicts/lists."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_objectid(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    return obj


# endpoints-------------
# 1.total number of jds and resumes
@match_router.get("/")
def total_resume_jds():
    try:
        total_resume = resume_collection.count_documents({})
        total_jd = jd_collection.count_documents({"is_active": True})

        return {
            "Resume": total_resume,
            "Job_Dicreption": total_jd
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching  data")

# 2.match resumes with list of JDs
@match_router.post("/match",dependencies=[Depends(required)])
async def run_matching(request: Request):
    try:
        graph = match_graph()
        session_id = str(uuid.uuid4())

        body = await request.json()
        jd_ids = body.get("jd_ids", []) 

        if not jd_ids:
            raise HTTPException(status_code=400, detail="No JD IDs provided.")

        converted_jd_ids = []
        for jd in jd_ids:
            if len(jd) == 36:
                try:
                    converted_jd_ids.append(uuid.UUID(jd))
                except Exception:
                    converted_jd_ids.append(jd)
            elif len(jd) == 24:
                try:
                    converted_jd_ids.append(ObjectId(jd))
                except Exception:
                    converted_jd_ids.append(jd)
            else:
                converted_jd_ids.append(jd)
        jd_list = get_jds_by_ids(converted_jd_ids)

        if not jd_list:
            raise HTTPException(status_code=404, detail="No matching JDs found for given IDs.")

        all_resumes = get_resumes()

        if not all_resumes:
            raise HTTPException(status_code=404, detail="No resumes found in folder.")

        resume = all_resumes[0]

        state: MatchState = {
            "session_id": session_id,
            "thread_id": str(uuid.uuid4()),
            "jd_list": jd_list,
            "resumes": [resume], 
            "current_resume_file":resume["resume_id"],
            "scores": {},
            "list_match": [],
            "total_resume": len(all_resumes),
            "resume_done": 0,
            "matches": [],
            "user_decision": "",
            "generate_qa": [],
            "input_values": {}
        }
        final_state = graph.invoke(
            state,
            config={
                "configurable": {
                    "session_id": session_id,
                    "thread_id": state["thread_id"]
                }
            }
        )

        raw_matches = final_state.get("matches", [])
        processed_matches = []

        for idx, match in enumerate(raw_matches):
            jd_id = jd_list[idx]["_id"] if idx < len(jd_list) else None
            processed_matches.append({
                "id": resume["resume_id"],   
                "jd_id": jd_id,             
                "matched": match.get("matched"),
                "explanation_for_score": match.get("explanation_for_score"),
                "explanation_not_for_score": match.get("explanation_not_for_score"),
            })

        match_doc = {
            "_id": session_id,
            "resume_ids": resume["resume_id"], 
            "matches": processed_matches,
        }

        try:
            match_collection.insert_one(match_doc)
        except Exception:
            match_collection.replace_one({"_id": session_id}, match_doc, upsert=True)

        return {
            "session_id": session_id,
            "matches": processed_matches,
            "resume_processed": resume["resume_id"],
            "total_resumes": len(all_resumes)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# 3.Generate Q&A Endpoint  

@match_router.post("/generate_qa", dependencies=[Depends(required)])
async def generate_qa(request: GenerateQARequest):
    try:
        jd_id = request.jd_id
        # convert to uuid if the len is 36
        if len(jd_id) == 36:
            try:
                jd_id = uuid.UUID(jd_id)
            except Exception:
                pass
        # convert to objectid
        elif len(jd_id) == 24:
            try:
                jd_id = ObjectId(jd_id)
            except Exception:
                pass

        # Fetch JD
        jd_doc = next(iter(get_jds_by_ids([jd_id])), None)
        if not jd_doc:
            raise HTTPException(status_code=404, detail="JD not found.")

        # Fetch Resume
        resume_doc = resume_collection.find_one({"_id": ObjectId(request.resume_id)})
        if not resume_doc:
            raise HTTPException(status_code=404, detail="Resume not found.")

        resume_doc["resume_id"] = str(resume_doc["_id"])

        state = {
            "session_id": str(uuid.uuid4()),
            "thread_id": str(uuid.uuid4()),
            "jd_list": [jd_doc],
            "resumes": [resume_doc],
            "current_resume_file": resume_doc["resume_id"],
            "scores": {},
            "list_match": [],
            "matches": [{
                "job_title": jd_doc.get("job_title", "Unknown Role"),
                "id": jd_doc.get("_id", "Unknown ID"),
                "skills": jd_doc.get("skills", []),
                "responsibilities": jd_doc.get("responsibilities", []),
                "job_summary": jd_doc.get("job_summary", "N/A")
            }],
            "user_decision": "",
            "generate_qa": [],
            "input_values": {
                "level": request.difficulty_level,
                "range_values": request.num_questions,
                "type_question": request.question_type,
                "question": request.question_type,
                "job_title": jd_doc.get("job_title", "Unknown Role")
            }
        }

        qa_state = generate_qa_node(state)
        qa_list = qa_state.get("generate_qa", [])

        inner_qa = []
        if qa_list:
            raw_qa = qa_list[0].get("qa", [])
            for idx, qa in enumerate(raw_qa, start=1):
                inner_qa.append({
                    f"question {idx}": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "result": {
                        "poor": False,
                        "average": False,
                        "good": False
                    }
                })

        new_block = {
            "question_level": request.difficulty_level.lower(),
            "qa": inner_qa
        }

        # Check if entry already exists for this JD + Resume
        existing_doc = qa_collection.find_one({
            "job_id": str(jd_doc.get("_id", "Unknown ID")),
            "resume_id": resume_doc["resume_id"]
        })

        if existing_doc:
            # If level already exists, append questions
            level_exists = False
            for section in existing_doc.get("qa", []):
                if section.get("question_level") == request.difficulty_level.lower():
                    section["qa"].extend(inner_qa)
                    level_exists = True
                    break

            if not level_exists:
                existing_doc["qa"].append(new_block)

            # Update in DB
            qa_collection.update_one(
                {"_id": existing_doc["_id"]},
                {"$set": {"qa": existing_doc["qa"]}}
            )

            final_output = existing_doc
        else:
            final_output = {
                "job_id": str(jd_doc.get("_id", "Unknown ID")),
                "job_title": jd_doc.get("job_title", "Unknown Role"),
                "resume_id": resume_doc["resume_id"],
                "qa": [new_block]
            }
            qa_collection.insert_one(convert_objectid(final_output))
            
        response_output = {
            "job_id": str(jd_doc.get("_id", "Unknown ID")),
            "job_title": jd_doc.get("job_title", "Unknown Role"),
            "resume_id": resume_doc["resume_id"],
            "number_of_questions": request.num_questions,
            "qa": inner_qa      
        }

        return response_output

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(match_router)

