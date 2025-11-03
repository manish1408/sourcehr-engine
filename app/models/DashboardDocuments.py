from typing import List, Dict
from typing import List
from app.helpers.Database import MongoDB
import os

from dotenv import load_dotenv

load_dotenv()

class DDModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="DashboardDocuments"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def get_all_laws(self) -> List[Dict]:
        cursor = self.collection.find({})
        results = await cursor.to_list(length=None)
        return results
