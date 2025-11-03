from bson import ObjectId
from app.models.QuizAttempt import QuizAttemptModel
from app.models.Quizzes import QuizModel
from app.schemas.QuizAttempt import AnswerSubmission
from fastapi import HTTPException
from typing import Dict, Optional

class QuizAttemptService:
    def __init__(self):
        self.quiz_attempt_model = QuizAttemptModel()
        self.quiz_model=QuizModel()

    async def create_attempt(self, quiz_id: str, user_id) -> dict:
        try:
            data={}
            data["quizId"]=quiz_id
            data["userId"]=user_id
            inserted_id = await self.quiz_attempt_model.create_attempt(data)
            return {
                "success": True,
                "data": inserted_id
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create quiz attempt: {str(e)}"
            }

    async def get_attempts(self, filters: dict = {}, page: int = 1, limit: int = 100) -> dict:
        try:
            limit=limit
            total = await self.quiz_model.collection.count_documents()
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            attempts = await self.quiz_attempt_model.get_attempts(filters, number_to_skip, limit)
            return {
                "success": True,
                "data": {
                    "attempts": attempts,
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
                "error": f"Unable to fetch attempts: {str(e)}"
            }
            
    async def push_answer(self, attempt_id: str, answer: AnswerSubmission) -> dict:
        try:
            result = await self.quiz_attempt_model.push_answer(attempt_id, answer)
            if not result:
                return {
                    "success": False,
                    "data": None,
                    "error": "Attempt not found or answer not pushed"
                }
            return {
                "success": True,
                "data": "Answer submitted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to submit answer: {str(e)}"
            }


    async def update_selected_answers(self, attempt_id: str, updates: AnswerSubmission) -> dict:
        try:
            success = await self.quiz_attempt_model.update_selected_answers(attempt_id, updates)
            if not success:
                return {
                    "success": False,
                    "data": None,
                    "error": "Attempt or question not found, or nothing was updated"
                }
            return {
                "success": True,
                "data": "Selected answers updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update selected answers :{str(e)}"
            }


    async def delete_attempt(self, attempt_id: str) -> dict:
        try:
            success = await self.quiz_attempt_model.delete_attempt(attempt_id)
            if not success:
                return {
                    "success": False,
                    "data": None,
                    "error": "Attempt not found"
                }
            return {
                "success": True,
                "data": "Attempt deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": str(e),
                "error": f"Unable to delete attempt: {str(e)}"
            }
            
    async def submit_quiz(self, attempt_id: str, quiz_id: str) -> Dict:
        try:
            attempt = await self.quiz_attempt_model.get_attempt_by_id({"_id":ObjectId(attempt_id)})
            if not attempt:
                return {"success": False, "data": None, "error": "Attempt not found"}

            attempt = attempt.model_dump()
            quiz = await self.quiz_model.get_quiz({"_id": ObjectId(quiz_id)})
            if not quiz:
                return {"success": False, "data": None, "error": "Quiz not found"}

            quiz = quiz.model_dump()

            answers = attempt.get("answers", [])
            total_questions = len(quiz.get("questions", []))
            score = 0
            for ans in answers:
                question = None
                for q in quiz["questions"]:
                    if str(q["id"]) == str(ans["questionId"]):
                        question = q
                        break  

                if not question:
                    continue  
                correct = set(question.get("correctAnswers", []))
                selected = set(ans.get("selectedOptions", []))
                if correct == selected:
                    score += question.get("rewardPoint", 0)  
            percentage = (score / sum(q.get("rewardPoint", 0) for q in quiz.get("questions", []))) * 100 if total_questions > 0 else 0
            update_data = {
                "score": score,
                "total": total_questions,
                "percentage": round(percentage, 2),
                "status": "SUBMITTED"
            }
            updated = await self.quiz_attempt_model.update_attempt(attempt_id, update_data)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update quiz attempt"
                }
            return {
                "success": True,
                "data": "Quiz submitted successfully and score calculated"
            }
        except Exception as e:
            return {
                "success": False,
                "data": str(e),
                "error": "Error while submitting quiz"
            }
            
    async def get_leaderboard(self, skip: int = 0, limit: int = 10) -> dict:
        try:
            leaderboard = await self.quiz_attempt_model.get_leaderboard(skip=skip, limit=limit)
            return {
                "success": True,
                "data": leaderboard
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to fetch leaderboard: {str(e)}"
            }
            
    async def get_user_submission(self, user_id, quiz_id):
        try:
            attempt = await self.quiz_attempt_model.get_attempt_by_id({"userId":user_id})
            if not attempt:
                return {"success": False, "data": None, "error": "Attempt not found"}

            attempt = attempt.model_dump()
            quiz = await self.quiz_model.get_quiz({"_id": ObjectId(quiz_id)})
            if not quiz:
                return {"success": False, "data": None, "error": "Quiz not found"}

            quiz = quiz.model_dump()
            data = {
            "quiz": quiz,
            "attempt": attempt
             }
            return {
                "success": True,
                "data": data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to fetch attempts {str(e)}"
            }
        
