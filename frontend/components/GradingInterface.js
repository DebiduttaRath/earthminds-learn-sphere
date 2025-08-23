import { useState, useEffect } from 'react';

export default function GradingInterface({ attemptId, showDetailedView = false }) {
  const [gradingResult, setGradingResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailedFeedback, setDetailedFeedback] = useState(null);
  const [showDetails, setShowDetails] = useState(showDetailedView);

  useEffect(() => {
    if (attemptId) {
      fetchGradingResult();
    }
  }, [attemptId]);

  const fetchGradingResult = async () => {
    setLoading(true);
    setError(null);

    try {
      // First get the grading summary
      const summaryResponse = await fetch(`/api/grade/summary/${attemptId}`);
      
      if (summaryResponse.ok) {
        const summaryData = await summaryResponse.json();
        setGradingResult(summaryData);

        // If quiz is not graded yet, grade it
        if (summaryData.status === 'not_graded') {
          const gradeResponse = await fetch('/api/grade/attempt', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              attempt_id: attemptId,
              auto_submit: true
            }),
          });

          if (gradeResponse.ok) {
            const gradeData = await gradeResponse.json();
            setGradingResult({
              ...summaryData,
              ...gradeData.grading_result,
              status: 'graded'
            });
          }
        }
      } else {
        const errorData = await summaryResponse.json();
        setError(errorData.detail || 'Failed to fetch grading results');
      }
    } catch (error) {
      console.error('Error fetching grading result:', error);
      setError('Error loading grading results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchDetailedFeedback = async () => {
    try {
      const response = await fetch('/api/grade/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          attempt_id: attemptId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setDetailedFeedback(data.feedback);
      }
    } catch (error) {
      console.error('Error fetching detailed feedback:', error);
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

  const getPerformanceMessage = (percentage) => {
    if (percentage >= 90) return 'Excellent work! Outstanding performance!';
    if (percentage >= 80) return 'Great job! You have a strong understanding.';
    if (percentage >= 70) return 'Good work! Keep practicing to improve.';
    if (percentage >= 60) return 'Fair performance. Review the concepts and practice more.';
    if (percentage >= 40) return 'Need more practice. Focus on understanding fundamentals.';
    return 'Requires significant improvement. Consider getting additional help.';
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border mb-3" role="status">
          <span className="visually-hidden">Loading results...</span>
        </div>
        <p>Loading your quiz results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        <i className="fas fa-exclamation-triangle me-2"></i>
        {error}
      </div>
    );
  }

  if (!gradingResult) {
    return (
      <div className="alert alert-info" role="alert">
        <i className="fas fa-info-circle me-2"></i>
        No grading results available.
      </div>
    );
  }

  return (
    <div className="grading-interface">
      {/* Results Header */}
      <div className="card mb-4">
        <div className="card-header bg-primary text-white">
          <h5 className="mb-0">
            <i className="fas fa-chart-line me-2"></i>
            Quiz Results
          </h5>
        </div>
        <div className="card-body">
          <div className="row text-center">
            <div className="col-md-3 mb-3">
              <div className="h2 mb-0">
                <span className={`text-${getPerformanceColor(gradingResult.summary?.percentage || 0)}`}>
                  {gradingResult.summary?.percentage || 0}%
                </span>
              </div>
              <small className="text-muted">Final Score</small>
            </div>
            <div className="col-md-3 mb-3">
              <div className="h2 mb-0">
                <span className={`badge bg-${getGradeColor(gradingResult.summary?.grade || 'E')} fs-4`}>
                  {gradingResult.summary?.grade || 'E'}
                </span>
              </div>
              <small className="text-muted">Grade</small>
            </div>
            <div className="col-md-3 mb-3">
              <div className="h2 mb-0">
                {gradingResult.summary?.correct_answers || 0}/{gradingResult.summary?.total_questions || 0}
              </div>
              <small className="text-muted">Correct Answers</small>
            </div>
            <div className="col-md-3 mb-3">
              <div className="h2 mb-0">
                {gradingResult.summary?.time_taken_minutes || 0}m
              </div>
              <small className="text-muted">Time Taken</small>
            </div>
          </div>
          
          <div className="alert alert-info mt-3" role="alert">
            <i className="fas fa-thumbs-up me-2"></i>
            {getPerformanceMessage(gradingResult.summary?.percentage || 0)}
          </div>
        </div>
      </div>

      {/* Performance Breakdown */}
      {gradingResult.performance_breakdown && Object.keys(gradingResult.performance_breakdown).length > 0 && (
        <div className="card mb-4">
          <div className="card-header">
            <h6 className="mb-0">
              <i className="fas fa-chart-bar me-2"></i>
              Performance Breakdown
            </h6>
          </div>
          <div className="card-body">
            <div className="row">
              {Object.entries(gradingResult.performance_breakdown).map(([type, perf]) => (
                <div key={type} className="col-md-6 mb-3">
                  <div className="card border-primary">
                    <div className="card-body">
                      <h6 className="card-title">{type}</h6>
                      <div className="d-flex justify-content-between mb-2">
                        <span>Accuracy:</span>
                        <span className={`badge bg-${getPerformanceColor((perf.correct / perf.total) * 100)}`}>
                          {perf.correct}/{perf.total}
                        </span>
                      </div>
                      <div className="progress">
                        <div 
                          className={`progress-bar bg-${getPerformanceColor((perf.correct / perf.total) * 100)}`}
                          style={{ width: `${(perf.correct / perf.total) * 100}%` }}
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

      {/* Detailed Feedback */}
      <div className="card mb-4">
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">
              <i className="fas fa-comments me-2"></i>
              Detailed Feedback
            </h6>
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={() => {
                setShowDetails(!showDetails);
                if (!showDetails && !detailedFeedback) {
                  fetchDetailedFeedback();
                }
              }}
            >
              {showDetails ? 'Hide Details' : 'Show Details'}
            </button>
          </div>
        </div>
        
        {showDetails && (
          <div className="card-body">
            {detailedFeedback ? (
              <div>
                {detailedFeedback.detailed_feedback && (
                  <div className="mb-4">
                    <h6>AI Performance Analysis</h6>
                    <div className="alert alert-info">
                      {detailedFeedback.detailed_feedback.recommendations?.map((rec, index) => (
                        <div key={index} className="mb-2">
                          <i className="fas fa-lightbulb me-2"></i>
                          {rec}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Question-by-question breakdown */}
                {detailedFeedback.answers && (
                  <div>
                    <h6>Question-by-Question Review</h6>
                    {detailedFeedback.answers.map((answer, index) => (
                      <div key={index} className="card mb-3">
                        <div className="card-body">
                          <div className="d-flex justify-content-between align-items-start mb-2">
                            <h6 className="mb-0">Question {index + 1}</h6>
                            <span className={`badge bg-${answer.is_correct ? 'success' : 'danger'}`}>
                              {answer.points_awarded}/{answer.max_points} points
                            </span>
                          </div>
                          
                          <p className="mb-2">{answer.question_text}</p>
                          
                          <div className="row">
                            <div className="col-md-6">
                              <strong>Your Answer:</strong>
                              <div className={`p-2 rounded mt-1 ${answer.is_correct ? 'bg-success bg-opacity-10' : 'bg-danger bg-opacity-10'}`}>
                                {answer.student_answer || 'No answer provided'}
                              </div>
                            </div>
                            <div className="col-md-6">
                              <strong>Correct Answer:</strong>
                              <div className="p-2 rounded mt-1 bg-success bg-opacity-10">
                                {answer.correct_answer}
                              </div>
                            </div>
                          </div>
                          
                          {answer.feedback && (
                            <div className="mt-3">
                              <strong>Feedback:</strong>
                              <div className="alert alert-light mt-1">
                                {answer.feedback}
                              </div>
                            </div>
                          )}
                          
                          {answer.explanation && (
                            <div className="mt-2">
                              <strong>Explanation:</strong>
                              <p className="text-muted mt-1">{answer.explanation}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-3">
                <div className="spinner-border mb-2" role="status">
                  <span className="visually-hidden">Loading feedback...</span>
                </div>
                <p>Generating detailed feedback...</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Study Recommendations */}
      <div className="card">
        <div className="card-header">
          <h6 className="mb-0">
            <i className="fas fa-book me-2"></i>
            Study Recommendations
          </h6>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-6">
              <h6 className="text-success">Strengths</h6>
              <ul className="list-unstyled">
                {gradingResult.summary?.accuracy_percentage > 80 && (
                  <li><i className="fas fa-check text-success me-2"></i>Strong overall understanding</li>
                )}
                {gradingResult.summary?.time_taken_minutes < 20 && (
                  <li><i className="fas fa-check text-success me-2"></i>Good time management</li>
                )}
                <li><i className="fas fa-check text-success me-2"></i>Completed the quiz</li>
              </ul>
            </div>
            <div className="col-md-6">
              <h6 className="text-warning">Areas for Improvement</h6>
              <ul className="list-unstyled">
                {gradingResult.summary?.accuracy_percentage < 60 && (
                  <li><i className="fas fa-exclamation-triangle text-warning me-2"></i>Review fundamental concepts</li>
                )}
                {gradingResult.summary?.time_taken_minutes > 25 && (
                  <li><i className="fas fa-exclamation-triangle text-warning me-2"></i>Work on time management</li>
                )}
                <li><i className="fas fa-lightbulb text-info me-2"></i>Practice more questions on this topic</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-3">
            <h6>Next Steps</h6>
            <div className="d-flex flex-wrap gap-2">
              <button className="btn btn-primary btn-sm">
                <i className="fas fa-redo me-1"></i>Retake Quiz
              </button>
              <button className="btn btn-success btn-sm">
                <i className="fas fa-book me-1"></i>Study Material
              </button>
              <button className="btn btn-info btn-sm">
                <i className="fas fa-comments me-1"></i>Ask Tutor
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .grading-interface {
          max-width: 900px;
          margin: 0 auto;
        }
      `}</style>
    </div>
  );
}
