 
import os
from app.helpers.Database import MongoDB

class SecondaryIndustrySlugModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="SecondaryIndustrySlug"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

