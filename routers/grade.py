from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.grading_service import grading_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class GradeAttemptRequest(BaseModel):
    attempt_id: str
    auto_submit: bool = False


class DetailedFeedbackRequest(BaseModel):
    attempt_id: str
    student_profile: Optional[Dict[str, Any]] = None


class PerformanceAnalyticsRequest(BaseModel):
    student_id: str
    subject: Optional[str] = None
    limit: int = 10


@router.post("/attempt")
async def grade_quiz_attempt(
    request: GradeAttemptRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Grade a completed quiz attempt"""
    try:
        result = await grading_service.grade_quiz_attempt(
            attempt_id=request.attempt_id,
            auto_submit=request.auto_submit
        )
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            elif "already graded" in result["error"].lower():
                raise HTTPException(status_code=400, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "grading_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error grading quiz attempt: {e}")
        raise HTTPException(status_code=500, detail="Failed to grade quiz attempt")


@router.post("/feedback")
async def get_detailed_feedback(
    request: DetailedFeedbackRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed AI-generated feedback for a quiz attempt"""
    try:
        result = await grading_service.provide_detailed_feedback(
            attempt_id=request.attempt_id,
            student_profile=request.student_profile
        )
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "feedback": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate detailed feedback")


@router.get("/analytics/{student_id}")
async def get_performance_analytics(
    student_id: str,
    subject: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive performance analytics for a student"""
    try:
        result = await grading_service.get_student_performance_analytics(
            student_id=student_id,
            subject=subject,
            limit=limit
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance analytics")


@router.get("/summary/{attempt_id}")
async def get_grading_summary(
    attempt_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a grading summary for a specific attempt"""
    try:
        from services.quiz_service import quiz_service
        
        # Get the quiz attempt details
        attempt_details = await quiz_service.get_quiz_attempt(attempt_id)
        
        if "error" in attempt_details:
            if "not found" in attempt_details["error"].lower():
                raise HTTPException(status_code=404, detail=attempt_details["error"])
            else:
                raise HTTPException(status_code=500, detail=attempt_details["error"])
        
        # Check if the attempt is graded
        if attempt_details.get("status") != "completed":
            return {
                "attempt_id": attempt_id,
                "status": "not_graded",
                "message": "Quiz attempt is not yet graded"
            }
        
        # Calculate summary statistics
        answers = attempt_details.get("answers", [])
        correct_answers = sum(1 for ans in answers if ans.get("is_correct", False))
        total_questions = len(answers)
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Categorize performance by question type or topic
        performance_by_type = {}
        for ans in answers:
            # This would require additional question metadata
            question_type = "general"  # Could be extracted from question metadata
            if question_type not in performance_by_type:
                performance_by_type[question_type] = {"correct": 0, "total": 0}
            
            performance_by_type[question_type]["total"] += 1
            if ans.get("is_correct", False):
                performance_by_type[question_type]["correct"] += 1
        
        return {
            "attempt_id": attempt_id,
            "status": "graded",
            "summary": {
                "total_score": attempt_details.get("score", 0),
                "max_score": attempt_details.get("max_score", 0),
                "percentage": attempt_details.get("percentage", 0),
                "grade": attempt_details.get("grade", ""),
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "accuracy_percentage": round(accuracy, 2),
                "time_taken_minutes": attempt_details.get("time_taken_minutes"),
                "completed_at": attempt_details.get("completed_at")
            },
            "performance_breakdown": performance_by_type,
            "quiz_info": attempt_details.get("quiz", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting grading summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve grading summary")


@router.get("/leaderboard")
async def get_leaderboard(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    time_period: str = "week",  # week, month, all_time
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """Get leaderboard for quiz performance"""
    try:
        from sqlalchemy import select, func, text
        from models import QuizAttempt, Quiz
        from datetime import datetime, timedelta
        
        # Calculate time filter
        time_filter = None
        if time_period == "week":
            time_filter = datetime.utcnow() - timedelta(days=7)
        elif time_period == "month":
            time_filter = datetime.utcnow() - timedelta(days=30)
        
        # Build query for leaderboard
        base_query = """
        SELECT 
            qa.student_id,
            COUNT(qa.id) as attempts,
            AVG(qa.score / qa.max_score * 100) as average_percentage,
            SUM(qa.score) as total_score,
            MAX(qa.completed_at) as last_attempt
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.status = 'completed'
        """
        
        params = {}
        
        if subject:
            base_query += " AND q.subject = :subject"
            params["subject"] = subject
        
        if grade_level:
            base_query += " AND q.grade_level = :grade_level"
            params["grade_level"] = grade_level
        
        if time_filter:
            base_query += " AND qa.completed_at >= :time_filter"
            params["time_filter"] = time_filter
        
        base_query += """
        GROUP BY qa.student_id
        ORDER BY average_percentage DESC, total_score DESC
        LIMIT :limit
        """
        params["limit"] = limit
        
        result = await db.execute(text(base_query), params)
        leaderboard_data = result.fetchall()
        
        leaderboard = []
        for i, row in enumerate(leaderboard_data, 1):
            leaderboard.append({
                "rank": i,
                "student_id": row.student_id,
                "attempts": row.attempts,
                "average_percentage": round(row.average_percentage, 2),
                "total_score": row.total_score,
                "last_attempt": row.last_attempt.isoformat() if row.last_attempt else None
            })
        
        return {
            "leaderboard": leaderboard,
            "filters": {
                "subject": subject,
                "grade_level": grade_level,
                "time_period": time_period
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve leaderboard")


@router.get("/statistics")
async def get_grading_statistics(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Get overall grading and performance statistics"""
    try:
        from sqlalchemy import text
        
        # Base statistics query
        base_query = """
        SELECT 
            COUNT(qa.id) as total_attempts,
            AVG(qa.score / qa.max_score * 100) as average_percentage,
            MIN(qa.score / qa.max_score * 100) as min_percentage,
            MAX(qa.score / qa.max_score * 100) as max_percentage,
            COUNT(DISTINCT qa.student_id) as unique_students,
            COUNT(DISTINCT qa.quiz_id) as unique_quizzes
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.status = 'completed'
        """
        
        params = {}
        
        if subject:
            base_query += " AND q.subject = :subject"
            params["subject"] = subject
        
        if grade_level:
            base_query += " AND q.grade_level = :grade_level"
            params["grade_level"] = grade_level
        
        result = await db.execute(text(base_query), params)
        stats = result.fetchone()
        
        # Grade distribution query
        grade_query = """
        SELECT 
            CASE 
                WHEN (qa.score / qa.max_score * 100) >= 91 THEN 'A1'
                WHEN (qa.score / qa.max_score * 100) >= 81 THEN 'A2'
                WHEN (qa.score / qa.max_score * 100) >= 71 THEN 'B1'
                WHEN (qa.score / qa.max_score * 100) >= 61 THEN 'B2'
                WHEN (qa.score / qa.max_score * 100) >= 51 THEN 'C1'
                WHEN (qa.score / qa.max_score * 100) >= 41 THEN 'C2'
                WHEN (qa.score / qa.max_score * 100) >= 33 THEN 'D'
                ELSE 'E'
            END as grade,
            COUNT(*) as count
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.status = 'completed'
        """
        
        if subject:
            grade_query += " AND q.subject = :subject"
        if grade_level:
            grade_query += " AND q.grade_level = :grade_level"
        
        grade_query += " GROUP BY grade ORDER BY grade"
        
        grade_result = await db.execute(text(grade_query), params)
        grade_distribution = [{"grade": row.grade, "count": row.count} for row in grade_result]
        
        return {
            "overall_statistics": {
                "total_attempts": stats.total_attempts or 0,
                "average_percentage": round(stats.average_percentage or 0, 2),
                "min_percentage": round(stats.min_percentage or 0, 2),
                "max_percentage": round(stats.max_percentage or 0, 2),
                "unique_students": stats.unique_students or 0,
                "unique_quizzes": stats.unique_quizzes or 0
            },
            "grade_distribution": grade_distribution,
            "filters": {
                "subject": subject,
                "grade_level": grade_level
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting grading statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve grading statistics")
