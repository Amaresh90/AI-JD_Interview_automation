from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

MongoClient()

MONGO_URI = "mongodb+srv://srirakshark0921:lnBQzUbmnBpBz3yY@cluster0.r5uvwsc.mongodb.net/JD?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "JD"
COLLECTION_NAME = "job_descriptions"

def get_mongo_collection():
    """Connect to MongoDB and return the collection."""
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print("connection error : ")
        print("\n")
        print(e)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    return collection

def get_all_jds():
    """Retrieve all job descriptions from the collection."""
    collection = get_mongo_collection()
    return list(collection.find({}, {"_id": 0}))  
