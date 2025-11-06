from app.models.Quizzes import QuizModel
from app.schemas.Quizzes import QuestionCreate, QuestionUpdate, QuizCreate
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException

class QuizService:
    def __init__(self):
        self.quiz_model = QuizModel()

    def create_quiz(self, data: QuizCreate,user_id) -> dict:
        try:
            quiz_data = data.model_dump(exclude_unset=True)
            quiz_data["createdBy"]=user_id
            inserted_id = self.quiz_model.create_quiz(quiz_data)
            return {
                "success": True,
                "data": str(inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create quiz: {str(e)}"
            }

    def list_quizzes(self, page: int = 1, limit: int = 10,user_id:str=None) -> dict:
        try:
            limit=limit
            total = self.quiz_model.collection.count_documents({"createdBy":user_id})
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            quizzes = self.quiz_model.list_quizzes({"createdBy":user_id}, number_to_skip, limit)
            return {
                "success": True,
                "data": {
                    "quizzes": quizzes,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to list quizzes: {str(e)}"
            }

    def get_quiz_by_id(self, quiz_id: str) -> dict:
        try:
            if not ObjectId.is_valid(quiz_id):
                raise HTTPException(status_code=400, detail="Invalid Quiz ID")
            quiz = self.quiz_model.get_quiz({"_id": ObjectId(quiz_id)})
            if not quiz:
                raise HTTPException(status_code=404, detail="Quiz not found")
            return {
                "success": True,
                "data": quiz.model_dump()
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get quiz: {str(e)}"
            }

    def update_quiz(self, quiz_id: str, data: dict) -> dict:
        try:
            if not ObjectId.is_valid(quiz_id):
                raise HTTPException(status_code=400, detail="Invalid Quiz ID")
            updated = self.quiz_model.update_quiz(quiz_id, data)
            if not updated:
                raise HTTPException(status_code=404, detail="Quiz not found or not updated")
            return {
                "success": True,
                "data": "Quiz updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update quiz: {str(e)}"
            }

    def delete_quiz(self, quiz_id: str) -> dict:
        try:
            if not ObjectId.is_valid(quiz_id):
                raise HTTPException(status_code=400, detail="Invalid Quiz ID")
            data = self.quiz_model.delete_quiz(quiz_id)
            return {
                "success": True,
                "data":  "Quiz deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete quiz: {str(e)}"
            }
            
    def add_question(self, quiz_id: str, question_data: QuestionCreate):
        try:
            data = self.quiz_model.add_question(quiz_id, question_data.model_dump())
            return {
                "success": True,
                "data":  "Question added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to add question: {str(e)}"
            }
            
    def update_question(self, quiz_id: str, question_id: str, updates: QuestionUpdate):
        try:
            data = self.quiz_model.update_question(
                quiz_id, question_id, updates.dict(exclude_unset=True,exclude_none=True)
            )
            return {
                "success": True,
                "data":  "Question updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update question: {str(e)}"
            }
            
    def remove_question(self, quiz_id: str, question_id: str):
        try:           
            data = self.quiz_model.remove_question(quiz_id, question_id)
            return {
                "success": True,
                "data":  "Question deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to remove question: {str(e)}"
            }
