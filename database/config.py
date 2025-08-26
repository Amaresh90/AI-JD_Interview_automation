from pymongo import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb://localhost:27017/"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.hr_db

hr_collection = db["user_collections"]
domain_collection = db["domain_collection"]
jd_collection = db["jd_collection"]
roles_collection = db["role_collection"]
login_collection = db["login_collection"]
resume_collection = db["resume_collection"]
match_collection = db["match_collection"]
qa_collection = db["qa_collection"]