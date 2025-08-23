import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import ChatInterface from '../components/ChatInterface';

export default function Tutor() {
  const [studentId, setStudentId] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [studentProfile, setStudentProfile] = useState({
    grade_level: '10',
    subject: 'Mathematics',
    language_preference: 'en-IN'
  });

  useEffect(() => {
    // Generate a unique student ID if not set
    if (!studentId) {
      const id = `student_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setStudentId(id);
    }
  }, [studentId]);

  const handleStartSession = async () => {
    try {
      const response = await fetch('/api/tutor/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: studentId,
          subject: studentProfile.subject,
          grade_level: studentProfile.grade_level,
          language_preference: studentProfile.language_preference
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
      } else {
        console.error('Failed to start session');
      }
    } catch (error) {
      console.error('Error starting session:', error);
    }
  };

  return (
    <>
      <Head>
        <title>AI Tutor - Educational Tutoring Platform</title>
        <meta name="description" content="Chat with AI tutor for personalized learning" />
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
              <Link href="/quiz" className="nav-link">
                <i className="fas fa-question-circle me-1"></i>Quizzes
              </Link>
              <Link href="/grade" className="nav-link">
                <i className="fas fa-chart-line me-1"></i>Analytics
              </Link>
            </div>
          </div>
        </nav>

        <div className="container">
          <div className="row">
            {/* Sidebar - Student Profile */}
            <div className="col-lg-3 mb-4">
              <div className="card">
                <div className="card-header">
                  <h5 className="mb-0">
                    <i className="fas fa-user me-2"></i>Learning Profile
                  </h5>
                </div>
                <div className="card-body">
                  <div className="mb-3">
                    <label className="form-label">Grade Level</label>
                    <select 
                      className="form-select"
                      value={studentProfile.grade_level}
                      onChange={(e) => setStudentProfile({...studentProfile, grade_level: e.target.value})}
                    >
                      {[6, 7, 8, 9, 10, 11, 12].map(grade => (
                        <option key={grade} value={grade.toString()}>Grade {grade}</option>
                      ))}
                    </select>
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Subject</label>
                    <select 
                      className="form-select"
                      value={studentProfile.subject}
                      onChange={(e) => setStudentProfile({...studentProfile, subject: e.target.value})}
                    >
                      <option value="Mathematics">Mathematics</option>
                      <option value="Physics">Physics</option>
                      <option value="Chemistry">Chemistry</option>
                      <option value="Biology">Biology</option>
                      <option value="History">History</option>
                      <option value="Geography">Geography</option>
                      <option value="English">English</option>
                      <option value="Hindi">Hindi</option>
                    </select>
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Language</label>
                    <select 
                      className="form-select"
                      value={studentProfile.language_preference}
                      onChange={(e) => setStudentProfile({...studentProfile, language_preference: e.target.value})}
                    >
                      <option value="en-IN">English (India)</option>
                      <option value="hi-IN">Hindi</option>
                    </select>
                  </div>

                  {!sessionId ? (
                    <button 
                      className="btn btn-primary w-100"
                      onClick={handleStartSession}
                    >
                      <i className="fas fa-play me-2"></i>
                      Start Tutoring Session
                    </button>
                  ) : (
                    <div className="alert alert-success">
                      <i className="fas fa-check-circle me-2"></i>
                      Session Active
                    </div>
                  )}

                  <hr />

                  <div className="mt-3">
                    <h6>Quick Tips</h6>
                    <ul className="list-unstyled small">
                      <li><i className="fas fa-lightbulb text-warning me-1"></i> Ask specific questions</li>
                      <li><i className="fas fa-lightbulb text-warning me-1"></i> Request examples</li>
                      <li><i className="fas fa-lightbulb text-warning me-1"></i> Ask for practice problems</li>
                      <li><i className="fas fa-lightbulb text-warning me-1"></i> Seek explanations</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Suggestions */}
              <div className="card mt-3">
                <div className="card-header">
                  <h6 className="mb-0">
                    <i className="fas fa-question-circle me-2"></i>Sample Questions
                  </h6>
                </div>
                <div className="card-body">
                  <div className="d-grid gap-2">
                    {studentProfile.subject === 'Mathematics' && (
                      <>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          Explain quadratic equations
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          How do I solve algebra problems?
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          What is trigonometry?
                        </button>
                      </>
                    )}
                    {studentProfile.subject === 'Physics' && (
                      <>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          Explain Newton's laws
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          What is electromagnetic induction?
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          How does a motor work?
                        </button>
                      </>
                    )}
                    {studentProfile.subject === 'Chemistry' && (
                      <>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          What is atomic structure?
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          Explain chemical bonding
                        </button>
                        <button className="btn btn-outline-primary btn-sm text-start">
                          How do acids and bases react?
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Main Chat Area */}
            <div className="col-lg-9">
              <div className="card h-100">
                <div className="card-header bg-primary text-white">
                  <h5 className="mb-0">
                    <i className="fas fa-robot me-2"></i>
                    AI Tutor - {studentProfile.subject} (Grade {studentProfile.grade_level})
                  </h5>
                </div>
                <div className="card-body p-0">
                  {sessionId ? (
                    <ChatInterface 
                      studentId={studentId}
                      sessionId={sessionId}
                      subject={studentProfile.subject}
                      gradeLevel={studentProfile.grade_level}
                    />
                  ) : (
                    <div className="d-flex align-items-center justify-content-center h-100" style={{minHeight: '400px'}}>
                      <div className="text-center">
                        <i className="fas fa-comments fa-3x text-muted mb-3"></i>
                        <h5>Welcome to AI Tutoring!</h5>
                        <p className="text-muted">
                          Set your learning profile and start a session to begin chatting with your AI tutor.
                        </p>
                        <button 
                          className="btn btn-primary"
                          onClick={handleStartSession}
                        >
                          <i className="fas fa-play me-2"></i>
                          Start Learning
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </>
  );
}
