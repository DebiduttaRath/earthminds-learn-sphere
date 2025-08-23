import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import GradingInterface from '../components/GradingInterface';

export default function Grade() {
  const [studentId, setStudentId] = useState('');
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [leaderboard, setLeaderboard] = useState([]);
  const [statistics, setStatistics] = useState(null);

  useEffect(() => {
    // Generate a unique student ID if not set
    if (!studentId) {
      const id = `student_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setStudentId(id);
    }
  }, []);

  useEffect(() => {
    if (studentId) {
      fetchAnalytics();
      fetchLeaderboard();
      fetchStatistics();
    }
  }, [studentId, selectedSubject]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const url = selectedSubject 
        ? `/api/grade/analytics/${studentId}?subject=${selectedSubject}`
        : `/api/grade/analytics/${studentId}`;
      
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      } else if (response.status === 500) {
        setAnalytics({ total_attempts: 0, analytics: 'No quiz attempts found' });
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setAnalytics({ total_attempts: 0, error: 'Failed to load analytics' });
    } finally {
      setLoading(false);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedSubject) params.append('subject', selectedSubject);
      params.append('time_period', 'month');
      params.append('limit', '10');

      const response = await fetch(`/api/grade/leaderboard?${params}`);
      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data.leaderboard || []);
      }
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  const fetchStatistics = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedSubject) params.append('subject', selectedSubject);

      const response = await fetch(`/api/grade/statistics?${params}`);
      if (response.ok) {
        const data = await response.json();
        setStatistics(data);
      }
    } catch (error) {
      console.error('Error fetching statistics:', error);
    }
  };

  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A1': case 'A2': return 'success';
      case 'B1': case 'B2': return 'primary';
      case 'C1': case 'C2': return 'warning';
      case 'D': return 'secondary';
      default: return 'danger';
    }
  };

  const getPerformanceColor = (percentage) => {
    if (percentage >= 80) return 'success';
    if (percentage >= 60) return 'warning';
    return 'danger';
  };

  return (
    <>
      <Head>
        <title>Grade Analytics - Educational Tutoring Platform</title>
        <meta name="description" content="View your performance analytics and grading" />
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
              <Link href="/quiz" className="nav-link">
                <i className="fas fa-question-circle me-1"></i>Quizzes
              </Link>
            </div>
          </div>
        </nav>

        <div className="container">
          {/* Header */}
          <div className="row mb-4">
            <div className="col-12">
              <div className="d-flex justify-content-between align-items-center">
                <h2>
                  <i className="fas fa-chart-line me-2"></i>
                  Performance Analytics
                </h2>
                <div className="d-flex gap-2">
                  <select
                    className="form-select"
                    value={selectedSubject}
                    onChange={(e) => setSelectedSubject(e.target.value)}
                    style={{width: 'auto'}}
                  >
                    <option value="">All Subjects</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Physics">Physics</option>
                    <option value="Chemistry">Chemistry</option>
                    <option value="Biology">Biology</option>
                    <option value="History">History</option>
                    <option value="Geography">Geography</option>
                  </select>
                  <button className="btn btn-outline-primary" onClick={fetchAnalytics}>
                    <i className="fas fa-refresh me-1"></i>Refresh
                  </button>
                </div>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2">Loading analytics...</p>
            </div>
          ) : (
            <div className="row">
              {/* Performance Overview */}
              <div className="col-lg-8">
                {analytics && analytics.total_attempts > 0 ? (
                  <>
                    {/* Performance Cards */}
                    <div className="row mb-4">
                      <div className="col-md-3 mb-3">
                        <div className="card bg-primary text-white">
                          <div className="card-body text-center">
                            <h4>{analytics.total_attempts}</h4>
                            <p className="mb-0">Total Attempts</p>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-3 mb-3">
                        <div className={`card bg-${getPerformanceColor(analytics.average_percentage)} text-white`}>
                          <div className="card-body text-center">
                            <h4>{analytics.average_percentage}%</h4>
                            <p className="mb-0">Average Score</p>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-3 mb-3">
                        <div className={`card bg-${getGradeColor(analytics.overall_grade)} text-white`}>
                          <div className="card-body text-center">
                            <h4>{analytics.overall_grade}</h4>
                            <p className="mb-0">Overall Grade</p>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-3 mb-3">
                        <div className="card bg-info text-white">
                          <div className="card-body text-center">
                            <h4>{Object.keys(analytics.subject_performance || {}).length}</h4>
                            <p className="mb-0">Subjects</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Subject Performance */}
                    {analytics.subject_performance && Object.keys(analytics.subject_performance).length > 0 && (
                      <div className="card mb-4">
                        <div className="card-header">
                          <h5 className="mb-0">
                            <i className="fas fa-chart-bar me-2"></i>Subject-wise Performance
                          </h5>
                        </div>
                        <div className="card-body">
                          <div className="row">
                            {Object.entries(analytics.subject_performance).map(([subject, perf]) => (
                              <div key={subject} className="col-md-6 mb-3">
                                <div className="card border-primary">
                                  <div className="card-body">
                                    <h6 className="card-title">{subject}</h6>
                                    <div className="d-flex justify-content-between mb-2">
                                      <span>Average: {perf.average_percentage.toFixed(1)}%</span>
                                      <span className={`badge bg-${getPerformanceColor(perf.average_percentage)}`}>
                                        {perf.attempts} attempts
                                      </span>
                                    </div>
                                    <div className="progress">
                                      <div 
                                        className={`progress-bar bg-${getPerformanceColor(perf.average_percentage)}`}
                                        style={{width: `${perf.average_percentage}%`}}
                                      ></div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Recent Trends */}
                    {analytics.recent_trends && analytics.recent_trends.length > 0 && (
                      <div className="card mb-4">
                        <div className="card-header">
                          <h5 className="mb-0">
                            <i className="fas fa-trending-up me-2"></i>Recent Performance Trends
                          </h5>
                        </div>
                        <div className="card-body">
                          <div className="table-responsive">
                            <table className="table table-striped">
                              <thead>
                                <tr>
                                  <th>Date</th>
                                  <th>Quiz</th>
                                  <th>Subject</th>
                                  <th>Score</th>
                                </tr>
                              </thead>
                              <tbody>
                                {analytics.recent_trends.slice(0, 10).map((trend, index) => (
                                  <tr key={index}>
                                    <td>{new Date(trend.date).toLocaleDateString()}</td>
                                    <td>{trend.quiz_title}</td>
                                    <td>{trend.subject}</td>
                                    <td>
                                      <span className={`badge bg-${getPerformanceColor(trend.percentage)}`}>
                                        {trend.percentage.toFixed(1)}%
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="card">
                    <div className="card-body text-center py-5">
                      <i className="fas fa-chart-line fa-3x text-muted mb-3"></i>
                      <h5>No Performance Data Available</h5>
                      <p className="text-muted">
                        Take some quizzes to see your performance analytics here.
                      </p>
                      <Link href="/quiz" className="btn btn-primary">
                        <i className="fas fa-question-circle me-2"></i>Take a Quiz
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {/* Sidebar */}
              <div className="col-lg-4">
                {/* Leaderboard */}
                <div className="card mb-4">
                  <div className="card-header">
                    <h6 className="mb-0">
                      <i className="fas fa-trophy me-2"></i>Monthly Leaderboard
                    </h6>
                  </div>
                  <div className="card-body">
                    {leaderboard.length > 0 ? (
                      <div className="list-group list-group-flush">
                        {leaderboard.slice(0, 5).map((student, index) => (
                          <div key={index} className="list-group-item d-flex justify-content-between align-items-center px-0">
                            <div className="d-flex align-items-center">
                              <span className={`badge ${
                                index === 0 ? 'bg-warning' : 
                                index === 1 ? 'bg-secondary' : 
                                index === 2 ? 'bg-warning' : 'bg-light text-dark'
                              } me-2`}>
                                #{student.rank}
                              </span>
                              <div>
                                <div className="fw-bold">
                                  {student.student_id === studentId ? 'You' : `Student ${student.student_id.slice(-4)}`}
                                </div>
                                <small className="text-muted">{student.attempts} attempts</small>
                              </div>
                            </div>
                            <span className={`badge bg-${getPerformanceColor(student.average_percentage)}`}>
                              {student.average_percentage}%
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted text-center">No leaderboard data available</p>
                    )}
                  </div>
                </div>

                {/* Overall Statistics */}
                {statistics && (
                  <div className="card mb-4">
                    <div className="card-header">
                      <h6 className="mb-0">
                        <i className="fas fa-chart-pie me-2"></i>Platform Statistics
                      </h6>
                    </div>
                    <div className="card-body">
                      <div className="mb-3">
                        <div className="d-flex justify-content-between">
                          <span>Total Attempts:</span>
                          <strong>{statistics.overall_statistics?.total_attempts || 0}</strong>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="d-flex justify-content-between">
                          <span>Platform Average:</span>
                          <strong>{statistics.overall_statistics?.average_percentage || 0}%</strong>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="d-flex justify-content-between">
                          <span>Active Students:</span>
                          <strong>{statistics.overall_statistics?.unique_students || 0}</strong>
                        </div>
                      </div>

                      {statistics.grade_distribution && statistics.grade_distribution.length > 0 && (
                        <>
                          <hr />
                          <h6 className="mb-2">Grade Distribution</h6>
                          {statistics.grade_distribution.map((grade, index) => (
                            <div key={index} className="d-flex justify-content-between align-items-center mb-1">
                              <span className={`badge bg-${getGradeColor(grade.grade)}`}>
                                {grade.grade}
                              </span>
                              <span>{grade.count} students</span>
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Quick Actions */}
                <div className="card">
                  <div className="card-header">
                    <h6 className="mb-0">
                      <i className="fas fa-bolt me-2"></i>Quick Actions
                    </h6>
                  </div>
                  <div className="card-body">
                    <div className="d-grid gap-2">
                      <Link href="/quiz" className="btn btn-primary btn-sm">
                        <i className="fas fa-question-circle me-1"></i>Take New Quiz
                      </Link>
                      <Link href="/tutor" className="btn btn-success btn-sm">
                        <i className="fas fa-comments me-1"></i>Start Tutoring
                      </Link>
                      <button className="btn btn-outline-primary btn-sm" onClick={fetchAnalytics}>
                        <i className="fas fa-refresh me-1"></i>Refresh Data
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </>
  );
}
