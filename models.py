from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

Base = declarative_base()


class Document(Base):
    """Educational documents and content"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100))  # NCERT, OpenStax, etc.
    subject = Column(String(100))
    grade_level = Column(String(50))
    language = Column(String(20), default="en-IN")
    document_type = Column(String(50))  # textbook, reference, etc.
    additional_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunked document content with embeddings for vector search"""
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
    additional_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class TutoringSession(Base):
    """Individual tutoring sessions with students"""
    __tablename__ = "tutoring_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(100), nullable=False)  # Can be user ID or session identifier
    subject = Column(String(100))
    grade_level = Column(String(50))
    language_preference = Column(String(20), default="en-IN")
    session_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("TutoringMessage", back_populates="session", cascade="all, delete-orphan")


class TutoringMessage(Base):
    """Messages within tutoring sessions"""
    __tablename__ = "tutoring_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("tutoring_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    additional_data = Column(JSON)  # For storing additional context, retrieved documents, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("TutoringSession", back_populates="messages")


class Quiz(Base):
    """Generated quizzes"""
    __tablename__ = "quizzes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    subject = Column(String(100), nullable=False)
    grade_level = Column(String(50))
    difficulty = Column(String(20))  # easy, medium, hard
    duration_minutes = Column(Integer)
    instructions = Column(Text)
    additional_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """Individual questions within quizzes"""
    __tablename__ = "quiz_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # mcq, short_answer, essay, etc.
    options = Column(JSON)  # For MCQ options
    correct_answer = Column(Text)
    explanation = Column(Text)
    points = Column(Float, default=1.0)
    order_index = Column(Integer, nullable=False)
    additional_data = Column(JSON)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    """Student attempts at quizzes"""
    __tablename__ = "quiz_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String(100), nullable=False)
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    score = Column(Float)
    max_score = Column(Float)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    time_taken_minutes = Column(Integer)
    additional_data = Column(JSON)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")


class QuizAnswer(Base):
    """Student answers to quiz questions"""
    __tablename__ = "quiz_answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id"), nullable=False)
    answer_text = Column(Text)
    is_correct = Column(Boolean)
    points_awarded = Column(Float, default=0.0)
    ai_feedback = Column(Text)  # AI-generated feedback
    grading_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("QuizQuestion")


class StudentProfile(Base):
    """Student profiles and learning analytics"""
    __tablename__ = "student_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200))
    grade_level = Column(String(50))
    preferred_subjects = Column(JSON)
    learning_style = Column(String(50))
    language_preference = Column(String(20), default="en-IN")
    performance_metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
