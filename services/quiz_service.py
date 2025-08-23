from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from models import Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from services.ai_service import ai_service
from services.vector_service import vector_service
from database import get_db
from config import settings
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class QuizService:
    """Service for quiz generation and management"""
    
    async def generate_quiz(
        self,
        topic: str,
        subject: str,
        grade_level: str,
        difficulty: str = "medium",
        num_questions: int = None,
        student_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a new quiz on the given topic"""
        try:
            num_questions = num_questions or settings.default_quiz_questions
            
            # Get relevant documents for context
            context_documents = await vector_service.search_by_topic(
                topic=topic,
                subject=subject,
                grade_level=grade_level,
                limit=10
            )
            
            # Generate quiz using AI
            quiz_generation_result = await ai_service.generate_quiz(
                topic=topic,
                subject=subject,
                grade_level=grade_level,
                difficulty=difficulty,
                num_questions=num_questions,
                context_documents=context_documents
            )
            
            if "error" in quiz_generation_result:
                return {"error": quiz_generation_result["error"]}
            
            quiz_data = quiz_generation_result["quiz_data"]
            
            # Save quiz to database
            async with get_db() as session:
                # Create quiz
                quiz = Quiz(
                    title=quiz_data.get("title", f"{topic} Quiz"),
                    subject=subject,
                    grade_level=grade_level,
                    difficulty=difficulty,
                    duration_minutes=quiz_data.get("duration_minutes", settings.quiz_time_limit_minutes),
                    instructions=quiz_data.get("instructions", "Answer all questions to the best of your ability."),
                    metadata={
                        "topic": topic,
                        "generated_by": "AI",
                        "context_documents_count": len(context_documents),
                        "tokens_used": quiz_generation_result.get("tokens_used", 0)
                    }
                )
                
                session.add(quiz)
                await session.flush()  # To get the quiz ID
                
                # Create questions
                questions = []
                for i, question_data in enumerate(quiz_data.get("questions", [])):
                    question = QuizQuestion(
                        quiz_id=quiz.id,
                        question_text=question_data.get("question"),
                        question_type=question_data.get("type", "mcq"),
                        options=question_data.get("options"),
                        correct_answer=question_data.get("correct_answer"),
                        explanation=question_data.get("explanation"),
                        points=question_data.get("points", 1.0),
                        order_index=i + 1,
                        metadata=question_data.get("metadata", {})
                    )
                    questions.append(question)
                    session.add(question)
                
                await session.commit()
                
                # Return quiz with questions
                return {
                    "quiz_id": str(quiz.id),
                    "title": quiz.title,
                    "subject": quiz.subject,
                    "grade_level": quiz.grade_level,
                    "difficulty": quiz.difficulty,
                    "duration_minutes": quiz.duration_minutes,
                    "instructions": quiz.instructions,
                    "questions": [
                        {
                            "id": str(q.id),
                            "question_text": q.question_text,
                            "question_type": q.question_type,
                            "options": q.options,
                            "points": q.points,
                            "order_index": q.order_index
                        }
                        for q in questions
                    ],
                    "metadata": quiz.metadata
                }
                
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {"error": str(e)}
    
    async def start_quiz_attempt(
        self,
        quiz_id: str,
        student_id: str
    ) -> Dict[str, Any]:
        """Start a new quiz attempt for a student"""
        try:
            async with get_db() as session:
                # Get quiz with questions
                quiz_query = select(Quiz).options(selectinload(Quiz.questions)).where(Quiz.id == uuid.UUID(quiz_id))
                result = await session.execute(quiz_query)
                quiz = result.scalar_one_or_none()
                
                if not quiz:
                    return {"error": "Quiz not found"}
                
                # Create quiz attempt
                attempt = QuizAttempt(
                    quiz_id=quiz.id,
                    student_id=student_id,
                    status="in_progress",
                    max_score=sum(q.points for q in quiz.questions),
                    started_at=datetime.utcnow(),
                    metadata={
                        "time_limit_minutes": quiz.duration_minutes,
                        "expected_end_time": (datetime.utcnow() + timedelta(minutes=quiz.duration_minutes)).isoformat()
                    }
                )
                
                session.add(attempt)
                await session.commit()
                
                # Return quiz data for student (without correct answers)
                return {
                    "attempt_id": str(attempt.id),
                    "quiz": {
                        "id": str(quiz.id),
                        "title": quiz.title,
                        "subject": quiz.subject,
                        "duration_minutes": quiz.duration_minutes,
                        "instructions": quiz.instructions,
                        "questions": [
                            {
                                "id": str(q.id),
                                "question_text": q.question_text,
                                "question_type": q.question_type,
                                "options": q.options,
                                "points": q.points,
                                "order_index": q.order_index
                            }
                            for q in sorted(quiz.questions, key=lambda x: x.order_index)
                        ]
                    },
                    "started_at": attempt.started_at.isoformat(),
                    "time_limit_minutes": quiz.duration_minutes
                }
                
        except Exception as e:
            logger.error(f"Error starting quiz attempt: {e}")
            return {"error": str(e)}
    
    async def submit_answer(
        self,
        attempt_id: str,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """Submit an answer for a quiz question"""
        try:
            async with get_db() as session:
                # Get attempt and question
                attempt_query = select(QuizAttempt).where(QuizAttempt.id == uuid.UUID(attempt_id))
                question_query = select(QuizQuestion).where(QuizQuestion.id == uuid.UUID(question_id))
                
                attempt_result = await session.execute(attempt_query)
                question_result = await session.execute(question_query)
                
                attempt = attempt_result.scalar_one_or_none()
                question = question_result.scalar_one_or_none()
                
                if not attempt or not question:
                    return {"error": "Attempt or question not found"}
                
                if attempt.status != "in_progress":
                    return {"error": "Quiz attempt is not active"}
                
                # Check if answer already exists
                existing_answer_query = select(QuizAnswer).where(
                    QuizAnswer.attempt_id == attempt.id,
                    QuizAnswer.question_id == question.id
                )
                existing_result = await session.execute(existing_answer_query)
                existing_answer = existing_result.scalar_one_or_none()
                
                if existing_answer:
                    # Update existing answer
                    existing_answer.answer_text = answer_text
                    answer = existing_answer
                else:
                    # Create new answer
                    answer = QuizAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        answer_text=answer_text
                    )
                    session.add(answer)
                
                await session.commit()
                
                return {
                    "answer_id": str(answer.id),
                    "status": "saved",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return {"error": str(e)}
    
    async def get_quiz_attempt(self, attempt_id: str) -> Dict[str, Any]:
        """Get quiz attempt details"""
        try:
            async with get_db() as session:
                query = select(QuizAttempt).options(
                    selectinload(QuizAttempt.quiz).selectinload(Quiz.questions),
                    selectinload(QuizAttempt.answers)
                ).where(QuizAttempt.id == uuid.UUID(attempt_id))
                
                result = await session.execute(query)
                attempt = result.scalar_one_or_none()
                
                if not attempt:
                    return {"error": "Quiz attempt not found"}
                
                return {
                    "id": str(attempt.id),
                    "quiz": {
                        "id": str(attempt.quiz.id),
                        "title": attempt.quiz.title,
                        "subject": attempt.quiz.subject,
                        "duration_minutes": attempt.quiz.duration_minutes
                    },
                    "status": attempt.status,
                    "score": attempt.score,
                    "max_score": attempt.max_score,
                    "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
                    "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                    "answers": [
                        {
                            "question_id": str(ans.question_id),
                            "answer_text": ans.answer_text,
                            "is_correct": ans.is_correct,
                            "points_awarded": ans.points_awarded,
                            "ai_feedback": ans.ai_feedback
                        }
                        for ans in attempt.answers
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting quiz attempt: {e}")
            return {"error": str(e)}


# Global quiz service instance
quiz_service = QuizService()
