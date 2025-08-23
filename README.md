# AI Educational Tutoring Platform

A comprehensive AI-powered educational platform designed for Indian students, featuring personalized tutoring, intelligent quiz generation, and automated grading aligned with NCERT curriculum standards.

## 🌟 Features

### 🤖 AI-Powered Tutoring
- Personalized learning conversations with AI tutor
- Context-aware responses based on educational materials
- Support for multiple subjects and grade levels
- Indian English optimization for local context

### 🧠 Intelligent Quiz Generation
- Automatic quiz creation from topics and educational content
- Difficulty-based question generation (Easy, Medium, Hard)
- Multiple question types: MCQ, Short Answer, Essay
- Real-time answer submission and progress tracking

### 📊 Smart Grading & Analytics
- AI-powered automated grading with detailed feedback
- Comprehensive performance analytics and insights
- Student progress tracking and learning recommendations
- Leaderboards and performance comparisons

### 📚 Vector-Based Content Search
- Educational document ingestion and processing
- Semantic search using vector embeddings
- NCERT and OpenStax content support
- Contextual content retrieval for tutoring

## 🚀 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** with **pgvector** - Vector database for similarity search
- **OpenAI API** - AI model integration for tutoring and grading
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation and serialization

### Frontend
- **Next.js** - React framework for web application
- **Bootstrap 5** - Responsive UI framework
- **Font Awesome** - Icon library

### AI & ML
- **OpenAI GPT-4** - Language model for tutoring and content generation
- **OpenAI Embeddings** - Text embeddings for vector search
- **Custom prompts** - Optimized for Indian educational context

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ with pgvector extension
- OpenAI API key

## 🛠️ Installation & Setup

### 1. Database Setup

```bash
# Install PostgreSQL and pgvector extension
# Create database
createdb tutoring_platform

# Install pgvector extension
psql tutoring_platform -c "CREATE EXTENSION vector;"

# Run schema setup
psql tutoring_platform < schema.sql
