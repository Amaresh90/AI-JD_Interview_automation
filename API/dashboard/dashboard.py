from fastapi import FastAPI, APIRouter, HTTPException
from pymongo import DESCENDING
from loguru import logger
from database.config import hr_collection,jd_collection,resume_collection

app = FastAPI()
dashboard_router = APIRouter()

@dashboard_router.get("/")
def get_dashboard():
    try:
        total_hr = hr_collection.count_documents({"role":{"$eq": "HR"}})
        users = hr_collection.count_documents({"role": {"$ne": "HR"}})
        active_jd = jd_collection.count_documents({"is_active": True})
        total_resume = resume_collection.count_documents({"is_selected": True})

        return {
            "total_hr": total_hr,
            "total_users": users,
            "total_active_jd": active_jd,
            "total_resume": total_resume
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching dashboard data")

@dashboard_router.get("/latest_users")
def get_latest_users():
    try:
        latest_users = list(
            hr_collection.find().sort("created_at", DESCENDING).limit(2)
        )
        for user in latest_users:
            user["_id"] = str(user["_id"])

        return {"latest_users": latest_users}
    except Exception as e:
        logger.error(f"Error fetching latest users: {e}")
        raise HTTPException(status_code=500, detail="Error fetching latest users")

app.include_router(dashboard_router)
