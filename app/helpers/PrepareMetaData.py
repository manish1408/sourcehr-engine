# from uuid import uuid4
# from langchain_core.documents import Document

# from app.helpers.VectorDB import VectorDB
# from app.models.LocationsSlug import LocationsSlugModel
# from app.models.PrimaryIndustrySlug import PrimaryIndustrySlugModel
# from app.models.RegionsSlug import RegionsSlugModel
# from app.models.SecondaryIndustrySlug import SecondaryIndustrySlugModel
# from app.models.TopicSlug import TopicSlugModel



# class PrepareMetaDataHelper:
#     def __init__(self):
#         self.location_slug_model = LocationsSlugModel()
#         self.primary_industry_slug_model = PrimaryIndustrySlugModel()
#         self.secondary_industry_slug_model = SecondaryIndustrySlugModel()
#         self.topics_slug_model = TopicSlugModel()
#         self.regions_slug_model = RegionsSlugModel()
        
#         self.location_slug_vector_db_helper = VectorDB("LocationsSlug")
#         self.primary_industry_slug_vector_db_helper = VectorDB("PrimaryIndustrySlug")
#         self.secondary_industry_slug_vector_db_helper = VectorDB("SecondaryIndustrySlug")
#         self.topics_slug_vector_db_helper = VectorDB("TopicSlug")
#         self.regions_slug_vector_db_helper = VectorDB("RegionsSlug")
        
        
#     def upload_location_slug_to_vector(self,title):
#         doc_id = str(uuid4())
#         doc = Document(
#                     page_content=title,
#                     metadata={}
#                 )
        
#         ids = self.location_slug_vector_db_helper.vector_store.add_documents(documents=[doc], ids=[doc_id])
        
#         return ids
    
#     def process_locations(self):
#         locations = self.location_slug_model.collection.find({})
        
#         for location in locations:
#             name = location.get("name","")
#             id = location.get("_id","")
#             vector_id = self.upload_location_slug_to_vector(name)
#             self.location_slug_model.collection.find_one_and_update({"_id":id},{"$push":{"vectorDocIds": vector_id}})
            
        
# from uuid import uuid4
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from langchain_core.documents import Document

# from app.helpers.VectorDB import VectorDB
# from app.models.LocationsSlug import LocationsSlugModel
# from app.models.PrimaryIndustrySlug import PrimaryIndustrySlugModel
# from app.models.RegionsSlug import RegionsSlugModel
# from app.models.SecondaryIndustrySlug import SecondaryIndustrySlugModel
# from app.models.TopicSlug import TopicSlugModel


# class PrepareMetaDataHelper:
#     def __init__(self):
#         # Models
#         self.models = {
#             "LocationsSlug": LocationsSlugModel(),
#             "PrimaryIndustrySlug": PrimaryIndustrySlugModel(),
#             "SecondaryIndustrySlug": SecondaryIndustrySlugModel(),
#             "TopicSlug": TopicSlugModel(),
#             "RegionsSlug": RegionsSlugModel(),
#         }

#         # VectorDB Helpers
#         self.vector_helpers = {
#             name: VectorDB(name)
#             for name in self.models.keys()
#         }

#     def upload_to_vector(self, namespace: str, title: str):
#         """Uploads a single title to the given namespace vector store."""
#         doc_id = str(uuid4())
#         doc = Document(page_content=title, metadata={})
#         ids = self.vector_helpers[namespace].vector_store.add_documents(
#             documents=[doc], ids=[doc_id]
#         )
#         return ids

#     def process_collection(self, namespace: str):
#         """Fetches all documents from a collection, uploads to vector, and updates DB."""
#         model = self.models[namespace]
#         collection = model.collection.find({ "vectorDocIds": { "$size": 0 } })

#         for item in collection:
#             name = item.get("name", "").strip()
#             if not name:
#                 continue

#             mongo_id = item.get("_id")
#             vector_id = self.upload_to_vector(namespace, name)

#             model.collection.find_one_and_update(
#                 {"_id": mongo_id},
#                 {"$push": {"vectorDocIds": vector_id}}
#             )

#     def process_all(self, max_workers: int = 15):
#         """Run all namespace processors in parallel using threads."""
#         results = {}
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             future_to_namespace = {
#                 executor.submit(self.process_collection, namespace): namespace
#                 for namespace in self.models.keys()
#             }

#             for future in as_completed(future_to_namespace):
#                 namespace = future_to_namespace[future]
#                 try:
#                     future.result()
#                     results[namespace] = "✅ Completed"
#                 except Exception as e:
#                     results[namespace] = f"❌ Failed: {e}"

#         return results


from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.documents import Document

from app.helpers.VectorDB import VectorDB
from app.models.TopicSlug import TopicSlugModel


class TopicMetaDataProcessor:
    def __init__(self):
        self.model = TopicSlugModel()
        self.vector_helper = VectorDB("TopicSlug")

    def upload_to_vector(self, title: str):
        """Uploads a single title to the TopicSlug vector store."""
        doc_id = str(uuid4())
        doc = Document(page_content=title, metadata={})
        ids = self.vector_helper.vector_store.add_documents(
            documents=[doc], ids=[doc_id]
        )
        return ids

    def _process_single_item(self, item: dict):
        """Uploads a single topic to vector DB and updates MongoDB."""
        name = item.get("name", "").strip()
        if not name:
            return

        mongo_id = item.get("_id")
        vector_id = self.upload_to_vector(name)

        self.model.collection.find_one_and_update(
            {"_id": mongo_id},
            {"$push": {"vectorDocIds": vector_id}}
        )

    def process_all_topics(self, max_workers: int = 15):
        """Processes all TopicSlug items in parallel using threads."""
        collection = self.model.collection.find({"vectorDocIds": {"$size": 0}})
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self._process_single_item, item): item
                for item in collection
            }

            for future in as_completed(future_to_item):
                try:
                    future.result()
                    results.append("✅")
                except Exception as e:
                    results.append(f"❌ {e}")

        return results