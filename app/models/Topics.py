import os
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.Topics import TopicSchema

class TopicsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Topics"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def create_topic(self, data: dict):
        """
        Create a new Topic document in the database.
        """
        data["created_at"] = datetime.utcnow()
        topic = TopicSchema(**data)
        result = self.collection.insert_one(topic.model_dump(by_alias=True))
        return result.inserted_id
    
    def get_topics(self):
        """
        Retrieve all topics from the database.
        """
        cursor = self.collection.find({})
        return [TopicSchema(**doc) for doc in cursor]