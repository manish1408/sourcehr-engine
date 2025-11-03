from app.helpers.Utilities import Utils
from app.helpers.AzureStorage import AzureBlobUploader
from bson import ObjectId
from app.models.User import UserModel

class ProfileService:
    def __init__(self):
        self.azure_uploader = AzureBlobUploader()
        self.user_model=UserModel()
    
    async def change_profile_picture(self, user_id: str, file):
        """Replace existing profile picture with a new one using the existing upload function."""
        try:
            if not ObjectId.is_valid(user_id):
                return {"success": False, "data": None, "error": "Invalid ObjectId format."}
            existing_profile = await self.profile_model.get_profile(ObjectId(user_id))
            if existing_profile and existing_profile.get("profilePic"):
                self.azure_uploader.delete_file(existing_profile["profilePic"])
            new_filename = self.azure_uploader.upload_profile_picture(file.file, file.filename)
            await self.profile_model.update_profile(ObjectId(user_id), new_filename)       
            return {"success": True, "data": f"Profile picture updated successfully with name {new_filename}"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
    async def update_user_info(self, user_id: str, data: dict):
        try:
            if not data:
                raise Exception("No data provided for update")
            updated = await self.user_model.update_user(user_id, data)
            if not updated:
                return {"success": True, "data": "No New changes in data."}
            return {"success": True, "data": "User info updated successfully"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
    async def get_current_user(self, token: str):
        try:
            # Decode token
            payload = Utils.decode_jwt_token(token)
            email = payload.get("email")
            hashed_password = payload.get("password") 
            if not email or not hashed_password:
                raise Exception("Email or password missing in token")
            user_doc = await self.user_model.collection.find_one({
                "email": email,
                "password": hashed_password
            })
            if not user_doc:
                raise Exception("Invalid credentials")

            user_doc["_id"] = str(user_doc["_id"])
            user_doc.pop("password", None)
            print(user_doc)
            return {
                "success": True,
                "data": user_doc
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
            
    async def save_onboarding(self, user_id: str, onboardingStep: int):
        try:
            if onboardingStep==3:
                
                resp = await self.user_model.update_user(user_id,{"onboardingStep":onboardingStep,"isOnboarded":True})
            else:
                resp = await self.user_model.update_user(user_id,{"onboardingStep":onboardingStep,"isOnboarded":False})

                
            return {
                    "success": True,
                    "data": "Changed" if resp else "No Change"
                }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

