from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.quiz_service import quiz_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class QuizGenerationRequest(BaseModel):
    topic: str
    subject: str
    grade_level: str
    difficulty: str = "medium"
    num_questions: int = 10
    student_id: Optional[str] = None


class QuizStartRequest(BaseModel):
    quiz_id: str
    student_id: str


class AnswerSubmissionRequest(BaseModel):
    attempt_id: str
    question_id: str
    answer_text: str


@router.post("/generate")
async def generate_quiz(
    request: QuizGenerationRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Generate a new quiz on the specified topic"""
    try:
        # Validate inputs
        if request.difficulty not in ["easy", "medium", "hard"]:
            raise HTTPException(status_code=400, detail="Difficulty must be easy, medium, or hard")
        
        if request.num_questions < 1 or request.num_questions > 50:
            raise HTTPException(status_code=400, detail="Number of questions must be between 1 and 50")
        
        # Generate quiz
        result = await quiz_service.generate_quiz(
            topic=request.topic,
            subject=request.subject,
            grade_level=request.grade_level,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            student_id=request.student_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "quiz": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.post("/start")
async def start_quiz(
    request: QuizStartRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Start a quiz attempt for a student"""
    try:
        result = await quiz_service.start_quiz_attempt(
            quiz_id=request.quiz_id,
            student_id=request.student_id
        )
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "attempt": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting quiz: {e}")
        raise HTTPException(status_code=500, detail="Failed to start quiz")


@router.post("/answer")
async def submit_answer(
    request: AnswerSubmissionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Submit an answer for a quiz question"""
    try:
        if not request.answer_text.strip():
            raise HTTPException(status_code=400, detail="Answer cannot be empty")
        
        result = await quiz_service.submit_answer(
            attempt_id=request.attempt_id,
            question_id=request.question_id,
            answer_text=request.answer_text.strip()
        )
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            elif "not active" in result["error"].lower():
                raise HTTPException(status_code=400, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit answer")


@router.get("/attempt/{attempt_id}")
async def get_quiz_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get quiz attempt details"""
    try:
        result = await quiz_service.get_quiz_attempt(attempt_id)
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quiz attempt: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quiz attempt")


@router.get("/suggestions")
async def get_quiz_suggestions(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Get quiz topic suggestions based on available educational content"""
    try:
        from services.vector_service import vector_service
        
        # Get document statistics to suggest topics
        suggestions = {
            "popular_topics": [
                "Algebra", "Geometry", "Trigonometry", "Calculus",
                "Physics Laws", "Chemical Reactions", "Cell Biology",
                "Indian History", "Geography", "Civics"
            ],
            "subjects": [
                "Mathematics", "Physics", "Chemistry", "Biology",
                "History", "Geography", "Civics", "English", "Hindi"
            ],
            "grade_levels": [
                "6", "7", "8", "9", "10", "11", "12"
            ],
            "difficulty_levels": ["easy", "medium", "hard"]
        }
        
        # Filter suggestions based on parameters
        if subject:
            # Add subject-specific topics
            subject_topics = {
                "Mathematics": ["Algebra", "Geometry", "Trigonometry", "Statistics", "Probability"],
                "Physics": ["Mechanics", "Thermodynamics", "Optics", "Electricity", "Magnetism"],
                "Chemistry": ["Atomic Structure", "Chemical Bonding", "Acids and Bases", "Organic Chemistry"],
                "Biology": ["Cell Biology", "Genetics", "Evolution", "Ecology", "Human Physiology"],
                "History": ["Ancient India", "Medieval India", "Modern India", "World History"],
                "Geography": ["Physical Geography", "Human Geography", "Indian Geography", "World Geography"]
            }
            suggestions["recommended_topics"] = subject_topics.get(subject, suggestions["popular_topics"])
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting quiz suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get quiz suggestions")


@router.get("/history/{student_id}")
async def get_quiz_history(
    student_id: str,
    limit: int = 10,
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Get quiz history for a student"""
    try:
        from sqlalchemy import select
        from models import QuizAttempt, Quiz
        
        query = select(QuizAttempt).join(Quiz).where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == "completed"
        )
        
        if subject:
            query = query.where(Quiz.subject == subject)
        
        query = query.order_by(QuizAttempt.completed_at.desc()).limit(limit)
        
        result = await db.execute(query)
        attempts = result.scalars().all()
        
        history = []
        for attempt in attempts:
            # Get quiz details
            quiz_query = select(Quiz).where(Quiz.id == attempt.quiz_id)
            quiz_result = await db.execute(quiz_query)
            quiz = quiz_result.scalar_one_or_none()
            
            if quiz:
                history.append({
                    "attempt_id": str(attempt.id),
                    "quiz": {
                        "id": str(quiz.id),
                        "title": quiz.title,
                        "subject": quiz.subject,
                        "grade_level": quiz.grade_level,
                        "difficulty": quiz.difficulty
                    },
                    "score": attempt.score,
                    "max_score": attempt.max_score,
                    "percentage": round((attempt.score / attempt.max_score * 100), 2) if attempt.max_score > 0 else 0,
                    "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                    "time_taken_minutes": attempt.time_taken_minutes
                })
        
        return {
            "student_id": student_id,
            "quiz_history": history,
            "total_attempts": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting quiz history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quiz history")


@router.delete("/attempt/{attempt_id}")
async def delete_quiz_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a quiz attempt (for cleanup or privacy)"""
    try:
        from sqlalchemy import select, delete
        from models import QuizAttempt
        
        # Check if attempt exists
        attempt_query = select(QuizAttempt).where(QuizAttempt.id == attempt_id)
        result = await db.execute(attempt_query)
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise HTTPException(status_code=404, detail="Quiz attempt not found")
        
        # Delete the attempt (answers will be cascade deleted)
        await db.execute(delete(QuizAttempt).where(QuizAttempt.id == attempt_id))
        await db.commit()
        
        return {"message": "Quiz attempt deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quiz attempt: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete quiz attempt")
