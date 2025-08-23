import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import QuizInterface from '../components/QuizInterface';

export default function Quiz() {
  const [studentId, setStudentId] = useState('');
  const [quizParams, setQuizParams] = useState({
    topic: '',
    subject: 'Mathematics',
    grade_level: '10',
    difficulty: 'medium',
    num_questions: 10
  });
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [quizHistory, setQuizHistory] = useState([]);
  const [suggestions, setSuggestions] = useState(null);

  useEffect(() => {
    // Generate a unique student ID if not set
    if (!studentId) {
      const id = `student_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setStudentId(id);
    }
    fetchSuggestions();
    fetchQuizHistory();
  }, [studentId]);

  const fetchSuggestions = async () => {
    try {
      const response = await fetch('/api/quiz/suggestions');
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data);
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  };

  const fetchQuizHistory = async () => {
    if (!studentId) return;
    
    try {
      const response = await fetch(`/api/quiz/history/${studentId}?limit=5`);
      if (response.ok) {
        const data = await response.json();
        setQuizHistory(data.quiz_history || []);
      }
    } catch (error) {
      console.error('Error fetching quiz history:', error);
    }
  };

  const handleGenerateQuiz = async () => {
    if (!quizParams.topic.trim()) {
      alert('Please enter a topic for the quiz');
      return;
    }

    setIsGenerating(true);
    try {
      const response = await fetch('/api/quiz/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...quizParams,
          student_id: studentId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setCurrentQuiz(data.quiz);
        } else {
          alert('Failed to generate quiz: ' + (data.error || 'Unknown error'));
        }
      } else {
        const errorData = await response.json();
        alert('Failed to generate quiz: ' + (errorData.detail || 'Server error'));
      }
    } catch (error) {
      console.error('Error generating quiz:', error);
      alert('Error generating quiz. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleQuizComplete = (result) => {
    setCurrentQuiz(null);
    fetchQuizHistory(); // Refresh history
    alert(`Quiz completed! Score: ${result.score}/${result.max_score}`);
  };

  const handleTopicSuggestionClick = (topic) => {
    setQuizParams({...quizParams, topic});
  };

  return (
    <>
      <Head>
        <title>AI Quiz Generator - Educational Tutoring Platform</title>
        <meta name="description" content="Generate and take AI-powered quizzes" />
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
      </Head>

      <div className="container-fluid">
        {/* Navigation */}
        <nav className="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
          <div className="container">
            <Link href="/" className="navbar-brand">
              <i className="fas fa-graduation-cap me-2"></i>
              AI Tutoring Platform
            </Link>
            <div className="navbar-nav ms-auto">
              <Link href="/" className="nav-link">
                <i className="fas fa-home me-1"></i>Home
              </Link>
              <Link href="/tutor" className="nav-link">
                <i className="fas fa-comments me-1"></i>Tutoring
              </Link>
              <Link href="/grade" className="nav-link">
                <i className="fas fa-chart-line me-1"></i>Analytics
              </Link>
            </div>
          </div>
        </nav>

        <div className="container">
          {!currentQuiz ? (
            <div className="row">
              {/* Quiz Generation Form */}
              <div className="col-lg-8">
                <div className="card">
                  <div className="card-header">
                    <h5 className="mb-0">
                      <i className="fas fa-brain me-2"></i>Generate AI Quiz
                    </h5>
                  </div>
                  <div className="card-body">
                    <div className="row">
                      <div className="col-md-6 mb-3">
                        <label className="form-label">Topic *</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g., Quadratic Equations, Photosynthesis"
                          value={quizParams.topic}
                          onChange={(e) => setQuizParams({...quizParams, topic: e.target.value})}
                        />
                      </div>
                      <div className="col-md-6 mb-3">
                        <label className="form-label">Subject</label>
                        <select
                          className="form-select"
                          value={quizParams.subject}
                          onChange={(e) => setQuizParams({...quizParams, subject: e.target.value})}
                        >
                          {suggestions?.subjects?.map(subject => (
                            <option key={subject} value={subject}>{subject}</option>
                          )) || [
                            <option key="math" value="Mathematics">Mathematics</option>,
                            <option key="physics" value="Physics">Physics</option>,
                            <option key="chemistry" value="Chemistry">Chemistry</option>,
                            <option key="biology" value="Biology">Biology</option>
                          ]}
                        </select>
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label">Grade Level</label>
                        <select
                          className="form-select"
                          value={quizParams.grade_level}
                          onChange={(e) => setQuizParams({...quizParams, grade_level: e.target.value})}
                        >
                          {suggestions?.grade_levels?.map(grade => (
                            <option key={grade} value={grade}>Grade {grade}</option>
                          )) || [6, 7, 8, 9, 10, 11, 12].map(grade => (
                            <option key={grade} value={grade.toString()}>Grade {grade}</option>
                          ))}
                        </select>
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label">Difficulty</label>
                        <select
                          className="form-select"
                          value={quizParams.difficulty}
                          onChange={(e) => setQuizParams({...quizParams, difficulty: e.target.value})}
                        >
                          <option value="easy">Easy</option>
                          <option value="medium">Medium</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label">Number of Questions</label>
                        <select
                          className="form-select"
                          value={quizParams.num_questions}
                          onChange={(e) => setQuizParams({...quizParams, num_questions: parseInt(e.target.value)})}
                        >
                          {[5, 10, 15, 20, 25].map(num => (
                            <option key={num} value={num}>{num} Questions</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <button
                      className="btn btn-primary"
                      onClick={handleGenerateQuiz}
                      disabled={isGenerating || !quizParams.topic.trim()}
                    >
                      {isGenerating ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2"></span>
                          Generating Quiz...
                        </>
                      ) : (
                        <>
                          <i className="fas fa-magic me-2"></i>
                          Generate Quiz
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Topic Suggestions */}
                {suggestions?.recommended_topics && (
                  <div className="card mt-3">
                    <div className="card-header">
                      <h6 className="mb-0">
                        <i className="fas fa-lightbulb me-2"></i>Topic Suggestions
                      </h6>
                    </div>
                    <div className="card-body">
                      <div className="d-flex flex-wrap gap-2">
                        {suggestions.recommended_topics.slice(0, 8).map((topic, index) => (
                          <button
                            key={index}
                            className="btn btn-outline-primary btn-sm"
                            onClick={() => handleTopicSuggestionClick(topic)}
                          >
                            {topic}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Sidebar */}
              <div className="col-lg-4">
                {/* Recent Quiz History */}
                <div className="card">
                  <div className="card-header">
                    <h6 className="mb-0">
                      <i className="fas fa-history me-2"></i>Recent Quizzes
                    </h6>
                  </div>
                  <div className="card-body">
                    {quizHistory.length > 0 ? (
                      <div className="list-group list-group-flush">
                        {quizHistory.map((quiz, index) => (
                          <div key={index} className="list-group-item px-0">
                            <div className="d-flex justify-content-between align-items-start">
                              <div className="flex-grow-1">
                                <h6 className="mb-1">{quiz.quiz?.title}</h6>
                                <p className="mb-1 small text-muted">
                                  {quiz.quiz?.subject} • Grade {quiz.quiz?.grade_level}
                                </p>
                                <small className="text-muted">
                                  Score: {quiz.percentage}%
                                </small>
                              </div>
                              <span className={`badge ${
                                quiz.percentage >= 80 ? 'bg-success' : 
                                quiz.percentage >= 60 ? 'bg-warning' : 'bg-danger'
                              }`}>
                                {quiz.percentage >= 80 ? 'Excellent' : 
                                 quiz.percentage >= 60 ? 'Good' : 'Needs Practice'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted text-center">
                        <i className="fas fa-question-circle fa-2x mb-2"></i><br />
                        No quizzes taken yet.<br />
                        Generate your first quiz!
                      </p>
                    )}
                  </div>
                </div>

                {/* Tips */}
                <div className="card mt-3">
                  <div className="card-header">
                    <h6 className="mb-0">
                      <i className="fas fa-tips me-2"></i>Quiz Tips
                    </h6>
                  </div>
                  <div className="card-body">
                    <ul className="list-unstyled small">
                      <li><i className="fas fa-check text-success me-1"></i> Read questions carefully</li>
                      <li><i className="fas fa-check text-success me-1"></i> Think before answering</li>
                      <li><i className="fas fa-check text-success me-1"></i> Review your answers</li>
                      <li><i className="fas fa-check text-success me-1"></i> Learn from feedback</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="row">
              <div className="col-12">
                <QuizInterface
                  quiz={currentQuiz}
                  studentId={studentId}
                  onComplete={handleQuizComplete}
                  onCancel={() => setCurrentQuiz(null)}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </>
  );
}
