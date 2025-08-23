from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from models import QuizAttempt, QuizAnswer, QuizQuestion
from services.ai_service import ai_service
from database import get_db
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GradingService:
    """Service for grading quiz attempts and providing feedback"""
    
    async def grade_quiz_attempt(
        self,
        attempt_id: str,
        auto_submit: bool = False
    ) -> Dict[str, Any]:
        """Grade a completed quiz attempt"""
        try:
            async with get_db() as session:
                # Get attempt with all related data
                query = select(QuizAttempt).options(
                    selectinload(QuizAttempt.quiz).selectinload(QuizAttempt.quiz.questions),
                    selectinload(QuizAttempt.answers)
                ).where(QuizAttempt.id == uuid.UUID(attempt_id))
                
                result = await session.execute(query)
                attempt = result.scalar_one_or_none()
                
                if not attempt:
                    return {"error": "Quiz attempt not found"}
                
                if attempt.status == "completed" and not auto_submit:
                    return {"error": "Quiz attempt already graded"}
                
                total_score = 0.0
                max_score = 0.0
                graded_answers = []
                
                # Grade each answer
                for question in attempt.quiz.questions:
                    max_score += question.points
                    
                    # Find student's answer for this question
                    student_answer = next(
                        (ans for ans in attempt.answers if ans.question_id == question.id),
                        None
                    )
                    
                    if student_answer:
                        # Grade the answer using AI
                        grading_result = await ai_service.grade_answer(
                            question=question.question_text,
                            student_answer=student_answer.answer_text,
                            correct_answer=question.correct_answer,
                            question_type=question.question_type,
                            context=question.explanation
                        )
                        
                        # Update answer with grading results
                        student_answer.is_correct = grading_result.get("is_correct", False)
                        student_answer.points_awarded = grading_result.get("score", 0) * question.points
                        student_answer.ai_feedback = grading_result.get("feedback", "")
                        student_answer.grading_metadata = {
                            "explanation": grading_result.get("explanation", ""),
                            "tokens_used": grading_result.get("tokens_used", 0),
                            "graded_at": datetime.utcnow().isoformat()
                        }
                        
                        total_score += student_answer.points_awarded
                        
                        graded_answers.append({
                            "question_id": str(question.id),
                            "question_text": question.question_text,
                            "student_answer": student_answer.answer_text,
                            "correct_answer": question.correct_answer,
                            "is_correct": student_answer.is_correct,
                            "points_awarded": student_answer.points_awarded,
                            "max_points": question.points,
                            "feedback": student_answer.ai_feedback,
                            "explanation": question.explanation
                        })
                    else:
                        # No answer provided
                        graded_answers.append({
                            "question_id": str(question.id),
                            "question_text": question.question_text,
                            "student_answer": None,
                            "correct_answer": question.correct_answer,
                            "is_correct": False,
                            "points_awarded": 0.0,
                            "max_points": question.points,
                            "feedback": "No answer provided",
                            "explanation": question.explanation
                        })
                
                # Update attempt with final scores
                attempt.score = total_score
                attempt.max_score = max_score
                attempt.status = "completed"
                attempt.completed_at = datetime.utcnow()
                attempt.time_taken_minutes = int(
                    (attempt.completed_at - attempt.started_at).total_seconds() / 60
                ) if attempt.started_at else None
                
                await session.commit()
                
                # Calculate percentage and grade
                percentage = (total_score / max_score * 100) if max_score > 0 else 0
                grade = self._calculate_grade(percentage)
                
                return {
                    "attempt_id": str(attempt.id),
                    "status": "completed",
                    "score": total_score,
                    "max_score": max_score,
                    "percentage": round(percentage, 2),
                    "grade": grade,
                    "time_taken_minutes": attempt.time_taken_minutes,
                    "completed_at": attempt.completed_at.isoformat(),
                    "answers": graded_answers,
                    "summary": self._generate_performance_summary(graded_answers, percentage)
                }
                
        except Exception as e:
            logger.error(f"Error grading quiz attempt: {e}")
            return {"error": str(e)}
    
    async def provide_detailed_feedback(
        self,
        attempt_id: str,
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Provide detailed AI-generated feedback for a quiz attempt"""
        try:
            # Get graded attempt
            grading_result = await self.grade_quiz_attempt(attempt_id)
            
            if "error" in grading_result:
                return grading_result
            
            # Generate comprehensive feedback using AI
            performance_analysis = await ai_service.analyze_student_performance(
                quiz_attempts=[{
                    "score": grading_result["score"],
                    "max_score": grading_result["max_score"],
                    "percentage": grading_result["percentage"],
                    "subject": grading_result.get("subject"),
                    "answers": grading_result["answers"]
                }],
                student_profile=student_profile
            )
            
            return {
                **grading_result,
                "detailed_feedback": performance_analysis
            }
            
        except Exception as e:
            logger.error(f"Error providing detailed feedback: {e}")
            return {"error": str(e)}
    
    async def get_student_performance_analytics(
        self,
        student_id: str,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get comprehensive performance analytics for a student"""
        try:
            async with get_db() as session:
                # Build query for student's quiz attempts
                query = select(QuizAttempt).options(
                    selectinload(QuizAttempt.quiz),
                    selectinload(QuizAttempt.answers)
                ).where(
                    QuizAttempt.student_id == student_id,
                    QuizAttempt.status == "completed"
                )
                
                if subject:
                    query = query.join(QuizAttempt.quiz).where(QuizAttempt.quiz.subject == subject)
                
                query = query.order_by(QuizAttempt.completed_at.desc()).limit(limit)
                
                result = await session.execute(query)
                attempts = result.scalars().all()
                
                if not attempts:
                    return {
                        "student_id": student_id,
                        "total_attempts": 0,
                        "analytics": "No quiz attempts found"
                    }
                
                # Calculate analytics
                total_attempts = len(attempts)
                total_score = sum(attempt.score or 0 for attempt in attempts)
                total_possible = sum(attempt.max_score or 0 for attempt in attempts)
                average_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
                
                subject_performance = {}
                recent_trends = []
                
                for attempt in attempts:
                    # Subject-wise performance
                    subject_name = attempt.quiz.subject
                    if subject_name not in subject_performance:
                        subject_performance[subject_name] = {
                            "attempts": 0,
                            "total_score": 0,
                            "total_possible": 0,
                            "average_percentage": 0
                        }
                    
                    subj_perf = subject_performance[subject_name]
                    subj_perf["attempts"] += 1
                    subj_perf["total_score"] += attempt.score or 0
                    subj_perf["total_possible"] += attempt.max_score or 0
                    subj_perf["average_percentage"] = (
                        subj_perf["total_score"] / subj_perf["total_possible"] * 100
                    ) if subj_perf["total_possible"] > 0 else 0
                    
                    # Recent trends
                    recent_trends.append({
                        "date": attempt.completed_at.isoformat() if attempt.completed_at else None,
                        "subject": subject_name,
                        "percentage": (attempt.score / attempt.max_score * 100) if attempt.max_score > 0 else 0,
                        "quiz_title": attempt.quiz.title
                    })
                
                return {
                    "student_id": student_id,
                    "total_attempts": total_attempts,
                    "average_percentage": round(average_percentage, 2),
                    "overall_grade": self._calculate_grade(average_percentage),
                    "subject_performance": subject_performance,
                    "recent_trends": recent_trends,
                    "analytics_generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting student performance analytics: {e}")
            return {"error": str(e)}
    
    def _calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade based on percentage (Indian grading system)"""
        if percentage >= 91:
            return "A1"
        elif percentage >= 81:
            return "A2"
        elif percentage >= 71:
            return "B1"
        elif percentage >= 61:
            return "B2"
        elif percentage >= 51:
            return "C1"
        elif percentage >= 41:
            return "C2"
        elif percentage >= 33:
            return "D"
        else:
            return "E"
    
    def _generate_performance_summary(self, answers: List[Dict], percentage: float) -> Dict[str, Any]:
        """Generate a performance summary"""
        correct_answers = sum(1 for ans in answers if ans["is_correct"])
        total_questions = len(answers)
        
        strengths = []
        areas_for_improvement = []
        
        # Simple analysis based on performance
        if percentage >= 80:
            strengths.append("Excellent overall performance")
        elif percentage >= 60:
            strengths.append("Good understanding of concepts")
        
        if percentage < 60:
            areas_for_improvement.append("Review fundamental concepts")
        
        if correct_answers < total_questions * 0.5:
            areas_for_improvement.append("Practice more questions on this topic")
        
        return {
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "accuracy_rate": round(correct_answers / total_questions * 100, 2) if total_questions > 0 else 0,
            "strengths": strengths,
            "areas_for_improvement": areas_for_improvement,
            "recommendation": self._get_recommendation(percentage)
        }
    
    def _get_recommendation(self, percentage: float) -> str:
        """Get study recommendation based on performance"""
        if percentage >= 90:
            return "Excellent work! Continue practicing to maintain this level."
        elif percentage >= 75:
            return "Good performance! Focus on areas where you lost marks to improve further."
        elif percentage >= 60:
            return "Fair performance. Review the concepts and practice more questions."
        elif percentage >= 40:
            return "Need more practice. Spend time understanding fundamental concepts."
        else:
            return "Requires significant improvement. Consider seeking additional help and regular practice."


# Global grading service instance
grading_service = GradingService()
