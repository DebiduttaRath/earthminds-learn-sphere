# Overview

AI Educational Tutoring Platform is a comprehensive educational system designed specifically for Indian students. The platform provides personalized AI-powered tutoring, intelligent quiz generation, and automated grading aligned with NCERT curriculum standards. The system uses advanced vector search capabilities to provide contextually relevant educational content and leverages OpenAI's GPT models for natural language interactions optimized for Indian English.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Next.js Framework**: React-based web application with server-side rendering capabilities
- **Bootstrap 5**: Responsive UI framework for consistent styling across devices
- **Component-Based Design**: Modular React components for chat interface, quiz interface, and grading interface
- **API Integration**: Frontend communicates with FastAPI backend through REST endpoints with proxy configuration

## Backend Architecture
- **FastAPI Framework**: Modern Python web framework providing high-performance async API endpoints
- **Router-Based Architecture**: Modular routing system with separate routers for tutoring, quiz generation, grading, and document management
- **Service Layer Pattern**: Business logic separated into dedicated service classes (AI service, document service, quiz service, grading service, vector service)
- **Async/Await Pattern**: Full async implementation for database operations and external API calls

## Data Storage Solutions
- **PostgreSQL with pgvector**: Primary database with vector extension for similarity search
- **SQLAlchemy ORM**: Database abstraction layer with async support
- **Vector Embeddings**: OpenAI text embeddings stored as vectors for semantic search
- **Document Chunking**: Large educational documents split into searchable chunks with overlapping content

## AI Integration Architecture
- **OpenAI GPT-4**: Primary language model for tutoring conversations and content generation
- **OpenAI Embeddings**: Text-to-vector conversion for semantic search capabilities
- **Custom Prompt Engineering**: Specialized prompts optimized for Indian educational context and English usage
- **Context-Aware Responses**: AI responses enhanced with relevant educational content retrieved through vector search

## Authentication and Session Management
- **Simple Student ID System**: Basic identification using generated student IDs
- **Session-Based Tutoring**: Persistent tutoring sessions with conversation history
- **Stateless Quiz Attempts**: Independent quiz attempts tracked by unique attempt IDs

# External Dependencies

## Core AI Services
- **OpenAI API**: GPT-4 for natural language processing, text generation, and automated grading
- **OpenAI Embeddings API**: text-embedding-3-small model for vector generation and semantic search

## Database Technologies
- **PostgreSQL**: Primary relational database for structured data storage
- **pgvector Extension**: Vector similarity search capabilities for educational content retrieval
- **Redis**: Caching layer for improved performance (configured but not actively used in current implementation)

## Frontend Dependencies
- **Next.js 14**: React framework with built-in routing and SSR capabilities
- **Bootstrap 5.3**: CSS framework for responsive design
- **Font Awesome 6**: Icon library for user interface elements

## Development and Deployment
- **asyncpg**: Async PostgreSQL driver for Python
- **Pydantic**: Data validation and settings management
- **uvicorn**: ASGI server for running FastAPI applications
- **SQLAlchemy**: ORM with async support for database operations

## Educational Content Integration
- **NCERT Curriculum**: Support for Indian national curriculum content
- **OpenStax Materials**: Integration with open educational resources
- **Document Processing**: Text chunking and embedding generation for searchable educational content