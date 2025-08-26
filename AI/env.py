from dotenv import load_dotenv
from os import getenv

load_dotenv()

ENVS_KEYS = {
    "GOOGLE_API_KEY": getenv("GOOGLE_API_KEY"),
    "FILE_PATH": getenv("FILE_PATH"),
    "JD_FILE": getenv("JD_FILE"),
    "JD_DATABASE.DB": getenv("JD_DATABASE.DB"),
    "AGENT_MANAGED_RESUMES": getenv("AGENT_MANAGED_RESUMES"),
    "MONGO_URI": getenv("MONGO_URI"),
    "RESUME_FOLDER": getenv("RESUME_FOLDER"),
    "MODEL": getenv("MODEL"),
    "DB_NAME": getenv("DB_NAME"),
    "COLLECTION_NAME": getenv("COLLECTION_NAME")
}



