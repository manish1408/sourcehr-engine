from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
import certifi

from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    client: MongoClient = None

    @classmethod
    def connect(cls, uri: str):
        cls.client = MongoClient(uri, tlsCAFile=certifi.where())

    @classmethod
    def get_database(cls, db_name: str):
        return cls.client[db_name]
    
    @classmethod
    def connection_status(cls):
        try:
            cls.client.admin.command('ping')
            return {"status": "connected", "db": os.getenv('DB_NAME')}
        except ConnectionFailure as e:
            return {"status": "disconnected", "db": os.getenv('DB_NAME')}