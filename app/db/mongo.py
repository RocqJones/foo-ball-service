from pymongo import MongoClient
from app.config.settings import settings
import certifi

client = MongoClient(
    settings.MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
)

db = client[settings.DB_NAME]

def get_collection(name: str):
    return db[name]
