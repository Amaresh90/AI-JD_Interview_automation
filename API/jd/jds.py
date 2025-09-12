from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from uuid import uuid4
import json
from AI.jd_backend import graph
from loguru import logger
from langgraph.types import Command
from database.config import jd_collection
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
import json
from datetime import datetime
from database.schema import jd_details
from typing import List

logger.add("jd_app.log", rotation="1 MB", retention="7 days", level="INFO")

app = FastAPI()
job_router = APIRouter()

jd_storage = {}

# ---------- Models ----------
class JDInput(BaseModel):
    job_title: str
    location: str
    job_type: str
    work_mode: str
    experience_required: str
    no_vacancies: int
    skills: list[str]


class JDUpdate(BaseModel):
    job_title: str | None = None
    location: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    experience_required: str | None = None
    no_vacancies: int | None = None
    skills: list[str] | None = None
    job_summary: str | None = None
    responsibilities: list[str] | None = None
    is_active: bool | None = None 

class JDModifyRequest(BaseModel):
    is_modify: bool
    description: str = None
    is_active : bool

class DeleteJDRequest(BaseModel):
    jd_ids: List[str]

def all_jd_details(jds):
    return [jd_details(jd) for jd in jds]

# ---------- Generate JD ----------
@job_router.post("/jd")
async def generate_jd(input_data: JDInput):
    user_input = {
        "job_title": input_data.job_title,
        "loc": input_data.location,
        "job_type": input_data.job_type,
        "work_mode": input_data.work_mode,
        "exp": input_data.experience_required,
        "no_vacancies": input_data.no_vacancies,
        "skills": ", ".join(input_data.skills)
    }
    session_id = str(uuid4())
    state = {
        "user_input": user_input,
        "session_id": session_id,
        "generated_jd": None,
        "modified_jd": None,
        "final_jd": None,
        "file_status": None,
        "feedback_choice": None,
        "modification_request": None,
        "modification_count": 0
    }
    config = {"configurable": {"thread_id": session_id}}
    logger.info(f"Invoking graph : {state}")
    result_state = graph.invoke(state, config=config)
    logger.info(f"result_state {result_state}")

    jd_data = json.loads(result_state["generated_jd"])

    jd_id = str(uuid4())
    now = datetime.utcnow()  
    jd_record = {
        "id": jd_id,
        "thread_id": session_id,
        "job_title": input_data.job_title,
        "location": input_data.location,
        "job_type": input_data.job_type,
        "work_mode": input_data.work_mode,
        "experience_required": input_data.experience_required,
        "no_vacancies": input_data.no_vacancies,
        "skills": input_data.skills,
        "job_summary": jd_data.get("job_summary", ""),
        "responsibilities": jd_data.get("responsibilities", []),
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    jd_storage[jd_id] = jd_record
    # Return session_id in the response
    return {"jd_record": jd_record, "thread_id": session_id}


@job_router.post("/verification/{jd_id}")
async def verification_post(jd_id: str, request: JDModifyRequest):
    logger.info(f"Verification request for JD ID: {jd_id}")

    jd_record = jd_storage.get(jd_id)
    if not jd_record:
        raise HTTPException(status_code=404, detail="JD ID not found in JD storage")

    thread_id = jd_record["thread_id"]

    feedback_choice = "modification" if request.is_modify else "generate"
    modification = request.description if request.is_modify else None

    # Prepare state
    state = {
        "user_input": {
            "job_title": jd_record["job_title"],
            "loc": jd_record["location"],
            "job_type": jd_record["job_type"],
            "work_mode": jd_record["work_mode"],
            "exp": jd_record["experience_required"],
            "no_vacancies": jd_record["no_vacancies"],
            "skills": ", ".join(jd_record["skills"])
        },
        "thread_id": thread_id,
        "generated_jd": jd_record.get("generated_jd"),
        "modified_jd": None,
        "final_jd": None,
        "file_status": None,
        "feedback_choice": feedback_choice,
        "modification_request": modification,
        "modification_count": jd_record.get("modification_count", 0),
    }

    result = graph.invoke(Command(resume=state), config={"configurable": {"thread_id": thread_id}})

    final_jd_raw = result.get("modified_jd") if feedback_choice == "modification" else result.get("generated_jd")

    # Parse JD result
    try:
        if isinstance(final_jd_raw, str):
            final_jd = json.loads(final_jd_raw) if final_jd_raw.strip().startswith("{") else {"job_description": final_jd_raw}
        elif isinstance(final_jd_raw, dict):
            final_jd = final_jd_raw
        else:
            final_jd = {"job_description": str(final_jd_raw)}
    except Exception:
        logger.exception("Failed to parse JD JSON")
        final_jd = {"job_description": str(final_jd_raw)}

 
    jd_record.update({
        **final_jd,
        "modification_description": modification,
        "is_active": request.is_active,   
        "updated_at": datetime.utcnow()
    })

    insert_result = jd_collection.insert_one(jd_record)
    jd_record["_id"] = str(insert_result.inserted_id)

    return jsonable_encoder({
        "message": f"JD {'modified' if feedback_choice == 'modification' else 'generated'} and saved",
        "jd": jd_record,
        "thread_id": thread_id
    })


# get jds

@job_router.get("/jd/list")
def get_all_jds_sync(active_only: bool = False):
    query_filter = {}
    if active_only:
        query_filter["is_active"] = True

    jds_cursor = jd_collection.find(query_filter).sort("created_at", -1)
    jds = []
    for jd in jds_cursor:
        jd["_id"] = str(jd["_id"])
        jds.append(jd)

    return jds


# update jd
@job_router.put("/update/{jd_id}")
async def update_jd(jd_id: str, update: JDUpdate):
    jd = jd_storage.get(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")
    update_data = update.dict(exclude_unset=True)
    jd.update(update_data)
    jd["updated_at"] = datetime.utcnow()
    jd_storage[jd_id] = jd
    return {"message": "JD updated successfully", "jd": jd}


# delete jd

@job_router.delete("/delete")
async def delete_jds(request: DeleteJDRequest):
    not_found, deleted = [], []

    for jd_id in request.jd_ids:
        result = jd_collection.delete_one({"id": jd_id})  # use UUID, not _id
        if result.deleted_count > 0:
            deleted.append(jd_id)
        else:
            not_found.append(jd_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="No JDs found to delete")

    return {
        "status_code": 200,
        "message": f"{len(deleted)} JDs deleted successfully",
        "deleted": deleted,
        "not_found": not_found
    }

app.include_router(job_router)
