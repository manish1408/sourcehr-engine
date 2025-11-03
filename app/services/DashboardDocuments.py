from app.models.Knowledge import KnowledgeModel
from app.models.Document import DocumentModel
from app.models.User import UserModel
from app.helpers.Utilities import Utils
from app.helpers.VectorDB import VectorDB
from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.AIChat import AIChat
from pydantic import ValidationError
from bson import ObjectId
from typing import List
import os
from app.models.DashboardDocuments import DDModel
from app.schemas.DashboardDocumentsSchema import FinalDocSchema
from dotenv import load_dotenv

load_dotenv()


class DDService:
    def __init__(self):
        self.model = DDModel()

    async def get_all_laws(self) -> dict:
        try:
            raw_data = await self.model.get_all_laws()
            for item in raw_data:
                item["_id"] = str(item["_id"])
            parsed_data = [FinalDocSchema(**item) for item in raw_data]
            return {
                "success": True,
                "data":[item.dict(by_alias=True) for item in parsed_data],
                "error": None
            }
        except ValidationError as e:
            error_details = e.errors()
            return {
                "success": False,
                "data": None,
                "error": f"Invalid data: {error_details}"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
