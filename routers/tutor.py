from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db_session
from models import TutoringSession, TutoringMessage, StudentProfile
from services.ai_service import ai_service
from services.vector_service import vector_service
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class TutorRequest(BaseModel):
    message: str
    student_id: str
    session_id: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[str] = None


class TutorResponse(BaseModel):
    response: str
    session_id: str
    context_used: int
    suggestions: Optional[List[str]] = None


class SessionCreate(BaseModel):
    student_id: str
    subject: str
    grade_level: str
    language_preference: str = "en-IN"


@router.post("/chat", response_model=TutorResponse)
async def chat_with_tutor(
    request: TutorRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Chat with AI tutor"""
    try:
        # Get or create tutoring session
        if request.session_id:
            session_query = select(TutoringSession).options(
                selectinload(TutoringSession.messages)
            ).where(TutoringSession.id == uuid.UUID(request.session_id))
            result = await db.execute(session_query)
            session = result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create new session
            session = TutoringSession(
                student_id=request.student_id,
                subject=request.subject,
                grade_level=request.grade_level
            )
            db.add(session)
            await db.flush()
        
        # Get student profile
        profile_query = select(StudentProfile).where(StudentProfile.student_id == request.student_id)
        profile_result = await db.execute(profile_query)
        student_profile = profile_result.scalar_one_or_none()
        
        profile_dict = None
        if student_profile:
            profile_dict = {
                "grade_level": student_profile.grade_level,
                "preferred_subjects": student_profile.preferred_subjects,
                "learning_style": student_profile.learning_style,
                "language_preference": student_profile.language_preference
            }
        
        # Get conversation history
        conversation_history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in sorted(session.messages, key=lambda x: x.created_at)[-10:]  # Last 10 messages
        ]
        
        # Search for relevant educational content
        search_subject = request.subject or session.subject
        search_grade = request.grade_level or session.grade_level
        
        context_documents = await vector_service.search_similar_documents(
            query=request.message,
            subject=search_subject,
            grade_level=search_grade,
            limit=5
        )
        
        # Generate AI response
        ai_response = await ai_service.generate_tutor_response(
            student_message=request.message,
            context_documents=context_documents,
            conversation_history=conversation_history,
            student_profile=profile_dict
        )
        
        if "error" in ai_response:
            raise HTTPException(status_code=500, detail=ai_response["error"])
        
        # Save messages to database
        user_message = TutoringMessage(
            session_id=session.id,
            role="user",
            content=request.message,
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
        assistant_message = TutoringMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response["response"],
            metadata={
                "context_documents": len(context_documents),
                "tokens_used": ai_response.get("tokens_used", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        db.add(user_message)
        db.add(assistant_message)
        await db.commit()
        
        # Generate suggestions for follow-up questions
        suggestions = [
            "Can you explain this with an example?",
            "What are the practical applications of this concept?",
            "Can you give me a practice problem on this topic?",
            "How is this concept used in real life?"
        ]
        
        return TutorResponse(
            response=ai_response["response"],
            session_id=str(session.id),
            context_used=ai_response.get("context_used", 0),
            suggestions=suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in tutor chat: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")


@router.post("/session")
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new tutoring session"""
    try:
        session = TutoringSession(
            student_id=request.student_id,
            subject=request.subject,
            grade_level=request.grade_level,
            language_preference=request.language_preference,
            session_metadata={
                "created_via": "api",
                "initial_subject": request.subject
            }
        )
        
        db.add(session)
        await db.commit()
        
        return {
            "session_id": str(session.id),
            "student_id": session.student_id,
            "subject": session.subject,
            "grade_level": session.grade_level,
            "created_at": session.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get tutoring session details"""
    try:
        query = select(TutoringSession).options(
            selectinload(TutoringSession.messages)
        ).where(TutoringSession.id == uuid.UUID(session_id))
        
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata
            }
            for msg in sorted(session.messages, key=lambda x: x.created_at)
        ]
        
        return {
            "id": str(session.id),
            "student_id": session.student_id,
            "subject": session.subject,
            "grade_level": session.grade_level,
            "language_preference": session.language_preference,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": messages,
            "message_count": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.get("/sessions/{student_id}")
async def get_student_sessions(
    student_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """Get tutoring sessions for a student"""
    try:
        query = select(TutoringSession).where(
            TutoringSession.student_id == student_id
        ).order_by(TutoringSession.updated_at.desc()).limit(limit)
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return [
            {
                "id": str(session.id),
                "subject": session.subject,
                "grade_level": session.grade_level,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "language_preference": session.language_preference
            }
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting student sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/recommendations/{student_id}")
async def get_study_recommendations(
    student_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get personalized study recommendations for a student"""
    try:
        # Get student profile
        profile_query = select(StudentProfile).where(StudentProfile.student_id == student_id)
        profile_result = await db.execute(profile_query)
        student_profile = profile_result.scalar_one_or_none()
        
        if not student_profile:
            return {"recommendations": ["Complete your profile to get personalized recommendations"]}
        
        # Get recent session topics
        recent_sessions_query = select(TutoringSession).where(
            TutoringSession.student_id == student_id
        ).order_by(TutoringSession.updated_at.desc()).limit(5)
        
        sessions_result = await db.execute(recent_sessions_query)
        recent_sessions = sessions_result.scalars().all()
        
        recent_topics = [session.subject for session in recent_sessions if session.subject]
        
        # Get document recommendations
        profile_dict = {
            "grade_level": student_profile.grade_level,
            "preferred_subjects": student_profile.preferred_subjects,
            "learning_style": student_profile.learning_style,
            "language_preference": student_profile.language_preference
        }
        
        document_recommendations = await vector_service.get_document_recommendations(
            student_profile=profile_dict,
            recent_topics=recent_topics
        )
        
        return {
            "student_id": student_id,
            "recommended_documents": document_recommendations[:5],
            "recent_topics": recent_topics,
            "study_suggestions": [
                f"Review {topic} concepts with practice problems" for topic in recent_topics[:3]
            ] + [
                "Try solving previous year question papers",
                "Focus on your weak areas identified in recent quizzes",
                "Practice numerical problems daily for better understanding"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a tutoring session"""
    try:
        session_query = select(TutoringSession).where(TutoringSession.id == uuid.UUID(session_id))
        result = await db.execute(session_query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        await db.delete(session)
        await db.commit()
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")
