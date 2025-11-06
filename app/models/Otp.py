import os
from datetime import datetime
from app.helpers.Database import MongoDB

class OTPModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="otpData"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def save_otp(self, email: str, otp: int):
        """Delete old OTP for email (if any) and save new one"""
        self.collection.delete_many({"email": email})  
        data = {
            "email": email,
            "otp": otp,
            "createdAt": datetime.utcnow()
        }
        self.collection.insert_one(data)

    def get_otp(self, email: str):
        """Retrieve OTP for a given email"""
        return self.collection.find_one({"email": email}, sort=[("created_at", -1)])

    def delete_otp(self, email: str):
        """Delete OTP record after successful verification"""
        self.collection.delete_many({"email": email})
