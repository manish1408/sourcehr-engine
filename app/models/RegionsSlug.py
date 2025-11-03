 
import os
from app.helpers.Database import MongoDB

class RegionsSlugModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="RegionsSlug"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

