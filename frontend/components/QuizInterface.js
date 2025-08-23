import { useState, useEffect } from 'react';

export default function QuizInterface({ quiz, studentId, onComplete, onCancel }) {
  const [attemptId, setAttemptId] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [quizStarted, setQuizStarted] = useState(false);

  useEffect(() => {
    if (quiz && !quizStarted) {
      startQuizAttempt();
    }
  }, [quiz]);

  useEffect(() => {
    if (timeRemaining !== null && timeRemaining > 0) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (timeRemaining === 0) {
      handleSubmitQuiz();
    }
  }, [timeRemaining]);

  const startQuizAttempt = async () => {
    try {
      const response = await fetch('/api/quiz/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          quiz_id: quiz.quiz_id,
          student_id: studentId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAttemptId(data.attempt.attempt_id);
        setTimeRemaining(data.attempt.time_limit_minutes * 60); // Convert to seconds
        setQuizStarted(true);
      } else {
        const errorData = await response.json();
        alert('Failed to start quiz: ' + (errorData.detail || 'Unknown error'));
        onCancel();
      }
    } catch (error) {
      console.error('Error starting quiz:', error);
      alert('Error starting quiz. Please try again.');
      onCancel();
    }
  };

  const handleAnswerChange = (questionId, answer) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }));
  };

  const saveAnswer = async (questionId, answer) => {
    if (!attemptId) return;

    try {
      await fetch('/api/quiz/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          attempt_id: attemptId,
          question_id: questionId,
          answer_text: answer
        }),
      });
    } catch (error) {
      console.error('Error saving answer:', error);
    }
  };

  const handleNext = () => {
    const currentQuestion = quiz.questions[currentQuestionIndex];
    const answer = answers[currentQuestion.id];
    
    if (answer) {
      saveAnswer(currentQuestion.id, answer);
    }

    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const handleSubmitQuiz = async () => {
    if (isSubmitting) return;
    
    setIsSubmitting(true);

    // Save current answer if any
    const currentQuestion = quiz.questions[currentQuestionIndex];
    const currentAnswer = answers[currentQuestion?.id];
    if (currentAnswer) {
      await saveAnswer(currentQuestion.id, currentAnswer);
    }

    try {
      const response = await fetch('/api/grade/attempt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          attempt_id: attemptId,
          auto_submit: true
        }),
      });

      if (response.ok) {
        const data = await response.json();
        onComplete(data.grading_result);
      } else {
        const errorData = await response.json();
        alert('Failed to submit quiz: ' + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error submitting quiz:', error);
      alert('Error submitting quiz. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getAnsweredCount = () => {
    return Object.keys(answers).filter(key => answers[key]?.trim()).length;
  };

  if (!quizStarted) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border mb-3" role="status">
          <span className="visually-hidden">Starting quiz...</span>
        </div>
        <p>Starting your quiz...</p>
      </div>
    );
  }

  const currentQuestion = quiz.questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / quiz.questions.length) * 100;

  return (
    <div className="quiz-interface">
      {/* Quiz Header */}
      <div className="card mb-3">
        <div className="card-header">
          <div className="row align-items-center">
            <div className="col-md-6">
              <h5 className="mb-0">{quiz.title}</h5>
              <small className="text-muted">
                {quiz.subject} • Grade {quiz.grade_level} • {quiz.difficulty}
              </small>
            </div>
            <div className="col-md-6 text-md-end">
              <div className="d-flex justify-content-md-end align-items-center gap-3">
                <div>
                  <i className="fas fa-clock me-1"></i>
                  <span className={timeRemaining < 300 ? 'text-danger fw-bold' : ''}>
                    {formatTime(timeRemaining)}
                  </span>
                </div>
                <div>
                  <i className="fas fa-check-circle me-1"></i>
                  {getAnsweredCount()}/{quiz.questions.length} answered
                </div>
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="progress mt-2" style={{ height: '4px' }}>
            <div 
              className="progress-bar bg-success" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Question */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h6 className="text-muted mb-0">
              Question {currentQuestionIndex + 1} of {quiz.questions.length}
            </h6>
            <span className="badge bg-primary">
              {currentQuestion.points} point{currentQuestion.points !== 1 ? 's' : ''}
            </span>
          </div>
          
          <h5 className="mb-4">{currentQuestion.question_text}</h5>

          {/* Answer Input */}
          {currentQuestion.question_type === 'mcq' && currentQuestion.options ? (
            <div className="mb-3">
              {currentQuestion.options.map((option, index) => (
                <div key={index} className="form-check mb-2">
                  <input
                    className="form-check-input"
                    type="radio"
                    name={`question-${currentQuestion.id}`}
                    id={`option-${index}`}
                    checked={answers[currentQuestion.id] === option}
                    onChange={() => handleAnswerChange(currentQuestion.id, option)}
                  />
                  <label className="form-check-label" htmlFor={`option-${index}`}>
                    {option}
                  </label>
                </div>
              ))}
            </div>
          ) : (
            <div className="mb-3">
              <textarea
                className="form-control"
                rows={4}
                placeholder="Type your answer here..."
                value={answers[currentQuestion.id] || ''}
                onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="card">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <button
                className="btn btn-outline-secondary me-2"
                onClick={handlePrevious}
                disabled={currentQuestionIndex === 0}
              >
                <i className="fas fa-chevron-left me-1"></i>
                Previous
              </button>
              
              {currentQuestionIndex < quiz.questions.length - 1 ? (
                <button
                  className="btn btn-primary"
                  onClick={handleNext}
                >
                  Next
                  <i className="fas fa-chevron-right ms-1"></i>
                </button>
              ) : (
                <button
                  className="btn btn-success"
                  onClick={handleSubmitQuiz}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2"></span>
                      Submitting...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-check me-1"></i>
                      Submit Quiz
                    </>
                  )}
                </button>
              )}
            </div>

            <div className="d-flex gap-2">
              <button
                className="btn btn-outline-danger"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                <i className="fas fa-times me-1"></i>
                Cancel
              </button>
            </div>
          </div>

          {/* Question Navigator */}
          <div className="mt-3">
            <small className="text-muted">Jump to question:</small>
            <div className="d-flex flex-wrap gap-1 mt-1">
              {quiz.questions.map((q, index) => (
                <button
                  key={q.id}
                  className={`btn btn-sm ${
                    index === currentQuestionIndex 
                      ? 'btn-primary' 
                      : answers[q.id] 
                        ? 'btn-success' 
                        : 'btn-outline-secondary'
                  }`}
                  onClick={() => setCurrentQuestionIndex(index)}
                  style={{ minWidth: '40px' }}
                >
                  {index + 1}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .quiz-interface {
          max-width: 800px;
          margin: 0 auto;
        }
        
        .form-check-label {
          cursor: pointer;
          width: 100%;
          padding: 8px;
          border-radius: 4px;
          transition: background-color 0.2s;
        }
        
        .form-check-label:hover {
          background-color: #f8f9fa;
        }
        
        .form-check-input:checked + .form-check-label {
          background-color: #e3f2fd;
        }
      `}</style>
    </div>
  );
}
