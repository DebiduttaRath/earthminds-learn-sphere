import { useState, useEffect } from 'react';
import Link from 'next/link';
import Head from 'next/head';

export default function Home() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/documents/statistics/overview');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>AI Educational Tutoring Platform</title>
        <meta name="description" content="AI-powered tutoring platform for Indian students" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
      </Head>

      <div className="container-fluid">
        {/* Navigation */}
        <nav className="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
          <div className="container">
            <a className="navbar-brand" href="#">
              <i className="fas fa-graduation-cap me-2"></i>
              AI Tutoring Platform
            </a>
            <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
              <span className="navbar-toggler-icon"></span>
            </button>
            <div className="collapse navbar-collapse" id="navbarNav">
              <ul className="navbar-nav ms-auto">
                <li className="nav-item">
                  <Link href="/tutor" className="nav-link">
                    <i className="fas fa-comments me-1"></i>Tutoring
                  </Link>
                </li>
                <li className="nav-item">
                  <Link href="/quiz" className="nav-link">
                    <i className="fas fa-question-circle me-1"></i>Quizzes
                  </Link>
                </li>
                <li className="nav-item">
                  <Link href="/grade" className="nav-link">
                    <i className="fas fa-chart-line me-1"></i>Analytics
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="container">
          <div className="row mb-5">
            <div className="col-lg-8 mx-auto text-center">
              <h1 className="display-4 mb-4">
                Welcome to AI Educational Tutoring Platform
              </h1>
              <p className="lead mb-4">
                Personalized learning for Indian students with AI-powered tutoring, 
                interactive quizzes, and intelligent grading aligned with NCERT curriculum.
              </p>
              <div className="d-flex justify-content-center gap-3 flex-wrap">
                <Link href="/tutor" className="btn btn-primary btn-lg">
                  <i className="fas fa-comments me-2"></i>Start Tutoring
                </Link>
                <Link href="/quiz" className="btn btn-outline-primary btn-lg">
                  <i className="fas fa-question-circle me-2"></i>Take a Quiz
                </Link>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="row mb-5">
            <div className="col-md-4 mb-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="feature-icon mb-3">
                    <i className="fas fa-robot fa-3x text-primary"></i>
                  </div>
                  <h5 className="card-title">AI-Powered Tutoring</h5>
                  <p className="card-text">
                    Get personalized explanations and guidance from our AI tutor 
                    trained on Indian educational content and NCERT curriculum.
                  </p>
                  <Link href="/tutor" className="btn btn-primary">
                    Start Learning
                  </Link>
                </div>
              </div>
            </div>
            
            <div className="col-md-4 mb-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="feature-icon mb-3">
                    <i className="fas fa-brain fa-3x text-success"></i>
                  </div>
                  <h5 className="card-title">Intelligent Quiz Generation</h5>
                  <p className="card-text">
                    Practice with automatically generated quizzes tailored to your 
                    grade level and subjects, with varying difficulty levels.
                  </p>
                  <Link href="/quiz" className="btn btn-success">
                    Take Quiz
                  </Link>
                </div>
              </div>
            </div>
            
            <div className="col-md-4 mb-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="feature-icon mb-3">
                    <i className="fas fa-chart-line fa-3x text-info"></i>
                  </div>
                  <h5 className="card-title">Smart Analytics</h5>
                  <p className="card-text">
                    Track your progress with detailed analytics and get 
                    personalized recommendations to improve your performance.
                  </p>
                  <Link href="/grade" className="btn btn-info">
                    View Analytics
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Statistics */}
          {!loading && stats && (
            <div className="row mb-5">
              <div className="col-12">
                <h3 className="text-center mb-4">Platform Statistics</h3>
                <div className="row">
                  <div className="col-md-3 col-sm-6 mb-3">
                    <div className="card bg-primary text-white text-center">
                      <div className="card-body">
                        <h4>{stats.total_documents || 0}</h4>
                        <p className="mb-0">Educational Documents</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-3 col-sm-6 mb-3">
                    <div className="card bg-success text-white text-center">
                      <div className="card-body">
                        <h4>{stats.total_chunks || 0}</h4>
                        <p className="mb-0">Knowledge Chunks</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-3 col-sm-6 mb-3">
                    <div className="card bg-info text-white text-center">
                      <div className="card-body">
                        <h4>{stats.by_subject?.length || 0}</h4>
                        <p className="mb-0">Subjects Available</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-3 col-sm-6 mb-3">
                    <div className="card bg-warning text-white text-center">
                      <div className="card-body">
                        <h4>{stats.by_grade_level?.length || 0}</h4>
                        <p className="mb-0">Grade Levels</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Subject Areas */}
          <div className="row mb-5">
            <div className="col-12">
              <h3 className="text-center mb-4">Subject Areas</h3>
              <div className="row">
                {[
                  { name: 'Mathematics', icon: 'calculator', color: 'primary' },
                  { name: 'Physics', icon: 'atom', color: 'success' },
                  { name: 'Chemistry', icon: 'flask', color: 'danger' },
                  { name: 'Biology', icon: 'leaf', color: 'info' },
                  { name: 'History', icon: 'landmark', color: 'warning' },
                  { name: 'Geography', icon: 'globe', color: 'secondary' }
                ].map((subject, index) => (
                  <div key={index} className="col-lg-2 col-md-4 col-sm-6 mb-3">
                    <div className={`card border-${subject.color} h-100`}>
                      <div className="card-body text-center">
                        <i className={`fas fa-${subject.icon} fa-2x text-${subject.color} mb-2`}></i>
                        <h6 className="card-title">{subject.name}</h6>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="row mb-5">
            <div className="col-12">
              <div className="card bg-light">
                <div className="card-body text-center">
                  <h4 className="mb-4">Ready to Start Learning?</h4>
                  <p className="mb-4">
                    Choose your learning path and begin your educational journey with our AI-powered platform.
                  </p>
                  <div className="d-flex justify-content-center gap-3 flex-wrap">
                    <Link href="/tutor" className="btn btn-primary">
                      <i className="fas fa-play me-2"></i>Start Tutoring Session
                    </Link>
                    <Link href="/quiz" className="btn btn-success">
                      <i className="fas fa-play me-2"></i>Take Practice Quiz
                    </Link>
                    <Link href="/grade" className="btn btn-info">
                      <i className="fas fa-chart-bar me-2"></i>View My Progress
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="bg-dark text-light py-4 mt-5">
          <div className="container">
            <div className="row">
              <div className="col-md-6">
                <h5>AI Educational Tutoring Platform</h5>
                <p>Empowering Indian students with AI-powered personalized learning.</p>
              </div>
              <div className="col-md-6 text-md-end">
                <p>&copy; 2025 AI Tutoring Platform. Built for Indian Education.</p>
              </div>
            </div>
          </div>
        </footer>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </>
  );
}
