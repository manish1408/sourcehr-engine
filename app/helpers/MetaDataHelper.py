
from app.models.Industries import IndustriesModel
from app.models.Locations import LocationsModel
from app.models.Topics import TopicsModel

class MetaDataHelper:
    def __init__(self):
        self.location_model=LocationsModel()
        self.industries_model=IndustriesModel()
        self.topics_model=TopicsModel()
        
    # This method checks if the event chunk has new data for region, country, or state
    # If any of these fields are present, it creates a new location document in the database
    def check_if_new_data(self, event_chunk):
        # if any([event_chunk.region, event_chunk.country, event_chunk.state]):
        #     location = {
        #         "region": event_chunk.region,
        #         "country": event_chunk.country,
        #         "state": event_chunk.state
        #     }
        #     self.location_model.create(location)
            
            

        if event_chunk.primary_industry and event_chunk.primary_industry_slug:
            primary_name = event_chunk.primary_industry
            primary_slug = event_chunk.primary_industry_slug

            secondary_entry = None
            if event_chunk.secondary_industry and event_chunk.secondary_industry_slug:
                secondary_entry = {
                    "name": event_chunk.secondary_industry,
                    "slug": event_chunk.secondary_industry_slug
                }

            # Check if primary industry already exists
            existing = self.industries_model.collection.find_one(
                {"primary_industry_slug": primary_slug}
            )

            if existing:
                if secondary_entry:
                    # Collect existing secondary slugs
                    existing_slugs = {
                        entry.get("slug") for entry in existing.get("secondary_industry", [])
                    }

                    if secondary_entry["slug"] not in existing_slugs:
                        self.industries_model.collection.update_one(
                            {"primary_industry_slug": primary_slug},
                            {"$addToSet": {"secondary_industry": secondary_entry}}
                        )
            else:
                # Create a new document for the primary industry
                industry_doc = {
                    "primary_industry": primary_name,
                    "primary_industry_slug": primary_slug,
                    "secondary_industry": [secondary_entry] if secondary_entry else []
                }
                self.industries_model.create(industry_doc)
            
        if event_chunk.topic:
            existing_topic = self.topics_model.collection.find_one(
                {"topic_slug": event_chunk.topic_slug}
            )
            if not existing_topic:
                # Create new topic document if it doesn't exist
                topic = {
                    "topic": event_chunk.topic,
                    "topic_slug": event_chunk.topic_slug
                }
                self.topics_model.create_topic(topic)
