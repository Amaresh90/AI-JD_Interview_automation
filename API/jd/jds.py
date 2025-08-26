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
from database.schema import all_jd_details,jd_details


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
    skills: list[str]


class JDUpdate(BaseModel):
    job_title: str | None = None
    location: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    experience_required: str | None = None
    skills: list[str] | None = None
    job_summary: str | None = None
    responsibilities: list[str] | None = None
    is_active: bool | None = None 

class JDModifyRequest(BaseModel):
    is_modify: bool
    description: str = None

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
    now = datetime.utcnow()  # current UTC datetime
    jd_record = {
        "id": jd_id,
        "thread_id": session_id,
        "job_title": input_data.job_title,
        "location": input_data.location,
        "job_type": input_data.job_type,
        "work_mode": input_data.work_mode,
        "experience_required": input_data.experience_required,
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


    # Fetch stored JD from in-memory storage
    jd_record = jd_storage.get(jd_id)
    if not jd_record:
        raise HTTPException(status_code=404, detail="JD ID not found in JD storage")


    thread_id = jd_record["thread_id"]


    feedback_choice = "modification" if request.is_modify else "generate"
    modification = request.description if request.is_modify else None


    logger.info(f"feedback_choice: {feedback_choice}")
    logger.info(f"modification: {modification}")


    user_input = {
        "job_title": jd_record["job_title"],
        "loc": jd_record["location"],
        "job_type": jd_record["job_type"],
        "work_mode": jd_record["work_mode"],
        "exp": jd_record["experience_required"],
        "skills": ", ".join(jd_record["skills"])
    }


    state = {
        "user_input": user_input,
        "thread_id": thread_id,
        "generated_jd": jd_record.get("generated_jd"),
        "modified_jd": None,
        "final_jd": None,
        "file_status": None,
        "feedback_choice": feedback_choice,
        "modification_request": modification,
        "modification_count": jd_record.get("modification_count", 0),
    }
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Invoking graph : {state}")
    result = graph.invoke(Command(resume=state), config=config)
    logger.info(f"result_state {result}")
    if feedback_choice == "generate":
        final_jd_raw = result.get("generated_jd")
    else:
        final_jd_raw = result.get("modified_jd")


    if not final_jd_raw:
        logger.error(f"No JD returned for feedback_choice={feedback_choice}")
        final_jd = {}
    else:
        try:
            if isinstance(final_jd_raw, str):
                final_jd = json.loads(final_jd_raw)
                if not isinstance(final_jd, dict):
                    final_jd = {"job_description": final_jd_raw}
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
        "is_active": jd_record.get("is_active", True),
        "updated_at": datetime.utcnow()
    })


    col = jd_collection
    insert_result = col.insert_one(jd_record)
    jd_record["_id"] = str(insert_result.inserted_id)


    logger.info(f"JD saved to MongoDB with _id: {jd_record['_id']}")


    return jsonable_encoder({
        "message": f"JD {'modified' if feedback_choice == 'modification' else 'generated'} and saved to MongoDB",
        "jd": jd_record,
        "thread_id": thread_id
    })


# get jds
@job_router.get("/get_jd")
async def get_all_jds():
    return list(jd_storage.values())


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
@job_router.delete("/delete/{jd_id}")
async def delete_jd(jd_id: str):
    if jd_id in jd_storage:
        del jd_storage[jd_id]
        return {"message": "JD is successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="JD not found")


app.include_router(job_router)
