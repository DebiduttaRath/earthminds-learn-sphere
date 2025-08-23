-- AI Educational Tutoring Platform Database Schema
-- PostgreSQL with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for educational content
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100),
    subject VARCHAR(100),
    grade_level VARCHAR(50),
    language VARCHAR(20) DEFAULT 'en-IN',
    document_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Document chunks with embeddings for vector search
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Student profiles
CREATE TABLE student_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200),
    grade_level VARCHAR(50),
    preferred_subjects JSONB,
    learning_style VARCHAR(50),
    language_preference VARCHAR(20) DEFAULT 'en-IN',
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tutoring sessions
CREATE TABLE tutoring_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id VARCHAR(100) NOT NULL,
    subject VARCHAR(100),
    grade_level VARCHAR(50),
    language_preference VARCHAR(20) DEFAULT 'en-IN',
    session_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Messages within tutoring sessions
CREATE TABLE tutoring_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES tutoring_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Quizzes
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    grade_level VARCHAR(50),
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    duration_minutes INTEGER,
    instructions TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Quiz questions
CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    options JSONB,
    correct_answer TEXT,
    explanation TEXT,
    points DECIMAL(5,2) DEFAULT 1.0,
    order_index INTEGER NOT NULL,
    metadata JSONB
);

-- Quiz attempts
CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    student_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    score DECIMAL(8,2),
    max_score DECIMAL(8,2),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    time_taken_minutes INTEGER,
    metadata JSONB
);

-- Quiz answers
CREATE TABLE quiz_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attempt_id UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    answer_text TEXT,
    is_correct BOOLEAN,
    points_awarded DECIMAL(5,2) DEFAULT 0.0,
    ai_feedback TEXT,
    grading_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance optimization

-- Documents indexes
CREATE INDEX idx_documents_subject ON documents(subject);
CREATE INDEX idx_documents_grade_level ON documents(grade_level);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_created_at ON documents(created_at);

-- Document chunks indexes
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Student profiles indexes
CREATE INDEX idx_student_profiles_student_id ON student_profiles(student_id);
CREATE INDEX idx_student_profiles_grade_level ON student_profiles(grade_level);

-- Tutoring sessions indexes
CREATE INDEX idx_tutoring_sessions_student_id ON tutoring_sessions(student_id);
CREATE INDEX idx_tutoring_sessions_subject ON tutoring_sessions(subject);
CREATE INDEX idx_tutoring_sessions_created_at ON tutoring_sessions(created_at);

-- Tutoring messages indexes
CREATE INDEX idx_tutoring_messages_session_id ON tutoring_messages(session_id);
CREATE INDEX idx_tutoring_messages_created_at ON tutoring_messages(created_at);

-- Quizzes indexes
CREATE INDEX idx_quizzes_subject ON quizzes(subject);
CREATE INDEX idx_quizzes_grade_level ON quizzes(grade_level);
CREATE INDEX idx_quizzes_difficulty ON quizzes(difficulty);
CREATE INDEX idx_quizzes_created_at ON quizzes(created_at);

-- Quiz questions indexes
CREATE INDEX idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);
CREATE INDEX idx_quiz_questions_order_index ON quiz_questions(order_index);

-- Quiz attempts indexes
CREATE INDEX idx_quiz_attempts_quiz_id ON quiz_attempts(quiz_id);
CREATE INDEX idx_quiz_attempts_student_id ON quiz_attempts(student_id);
CREATE INDEX idx_quiz_attempts_status ON quiz_attempts(status);
CREATE INDEX idx_quiz_attempts_completed_at ON quiz_attempts(completed_at);

-- Quiz answers indexes
CREATE INDEX idx_quiz_answers_attempt_id ON quiz_answers(attempt_id);
CREATE INDEX idx_quiz_answers_question_id ON quiz_answers(question_id);

-- Composite indexes for common queries
CREATE INDEX idx_documents_subject_grade ON documents(subject, grade_level);
CREATE INDEX idx_quiz_attempts_student_status ON quiz_attempts(student_id, status);
CREATE INDEX idx_tutoring_sessions_student_subject ON tutoring_sessions(student_id, subject);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_student_profiles_updated_at BEFORE UPDATE ON student_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tutoring_sessions_updated_at BEFORE UPDATE ON tutoring_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries

-- Student performance view
CREATE VIEW student_performance AS
SELECT 
    qa.student_id,
    q.subject,
    q.grade_level,
    COUNT(qa.id) as total_attempts,
    AVG(qa.score / qa.max_score * 100) as average_percentage,
    MAX(qa.completed_at) as last_attempt,
    SUM(qa.score) as total_score
FROM quiz_attempts qa
JOIN quizzes q ON qa.quiz_id = q.id
WHERE qa.status = 'completed'
GROUP BY qa.student_id, q.subject, q.grade_level;

-- Subject statistics view
CREATE VIEW subject_statistics AS
SELECT 
    d.subject,
    COUNT(d.id) as document_count,
    COUNT(dc.id) as chunk_count,
    COUNT(DISTINCT d.grade_level) as grade_levels_covered
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
GROUP BY d.subject;

-- Quiz performance view
CREATE VIEW quiz_performance AS
SELECT 
    q.id as quiz_id,
    q.title,
    q.subject,
    q.grade_level,
    q.difficulty,
    COUNT(qa.id) as total_attempts,
    AVG(qa.score / qa.max_score * 100) as average_score,
    MIN(qa.score / qa.max_score * 100) as min_score,
    MAX(qa.score / qa.max_score * 100) as max_score
FROM quizzes q
LEFT JOIN quiz_attempts qa ON q.id = qa.quiz_id AND qa.status = 'completed'
GROUP BY q.id, q.title, q.subject, q.grade_level, q.difficulty;

-- Comments for documentation
COMMENT ON TABLE documents IS 'Educational documents and content for vector search';
COMMENT ON TABLE document_chunks IS 'Chunked document content with embeddings for similarity search';
COMMENT ON TABLE student_profiles IS 'Student profiles and learning preferences';
COMMENT ON TABLE tutoring_sessions IS 'AI tutoring conversation sessions';
COMMENT ON TABLE tutoring_messages IS 'Individual messages within tutoring sessions';
COMMENT ON TABLE quizzes IS 'Generated quizzes and assessments';
COMMENT ON TABLE quiz_questions IS 'Individual questions within quizzes';
COMMENT ON TABLE quiz_attempts IS 'Student attempts at taking quizzes';
COMMENT ON TABLE quiz_answers IS 'Student answers to quiz questions with AI grading';

COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding for similarity search (1536 dimensions for OpenAI)';
COMMENT ON COLUMN quiz_attempts.status IS 'Status of quiz attempt: in_progress, completed, or abandoned';
COMMENT ON COLUMN quiz_answers.is_correct IS 'Whether the answer is correct (determined by AI grading)';
COMMENT ON COLUMN quiz_answers.ai_feedback IS 'AI-generated feedback for the student answer';

-- Sample data insertion (for development/testing)
-- This would typically be handled by the application, but included for reference

-- INSERT INTO documents (title, content, source, subject, grade_level, document_type) VALUES
-- ('Introduction to Algebra', 'Algebra is a branch of mathematics...', 'NCERT', 'Mathematics', '8', 'textbook'),
-- ('Laws of Motion', 'Newton''s laws of motion describe...', 'NCERT', 'Physics', '9', 'textbook'),
-- ('Cell Structure', 'A cell is the basic unit of life...', 'NCERT', 'Biology', '9', 'textbook');

-- Grant permissions (adjust as needed for your deployment)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tutoring_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tutoring_app;
