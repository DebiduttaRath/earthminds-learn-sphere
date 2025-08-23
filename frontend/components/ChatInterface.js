import { useState, useEffect, useRef } from 'react';

export default function ChatInterface({ studentId, sessionId, subject, gradeLevel }) {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      loadSessionMessages();
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSessionMessages = async () => {
    try {
      const response = await fetch(`/api/tutor/session/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Error loading session messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: currentMessage,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/tutor/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: currentMessage,
          student_id: studentId,
          session_id: sessionId,
          subject: subject,
          grade_level: gradeLevel
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage = {
          role: 'assistant',
          content: data.response,
          created_at: new Date().toISOString(),
          metadata: {
            context_used: data.context_used
          }
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        setSuggestions(data.suggestions || []);
      } else {
        const errorData = await response.json();
        const errorMessage = {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${errorData.detail || 'Please try again.'}`,
          created_at: new Date().toISOString(),
          error: true
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting right now. Please try again.',
        created_at: new Date().toISOString(),
        error: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setCurrentMessage(suggestion);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="d-flex flex-column h-100" style={{ minHeight: '500px' }}>
      {/* Chat Messages */}
      <div className="flex-grow-1 overflow-auto p-3" style={{ maxHeight: '400px' }}>
        {messages.length === 0 ? (
          <div className="text-center text-muted py-4">
            <i className="fas fa-comments fa-2x mb-2"></i>
            <p>Welcome! Ask me anything about {subject}. I'm here to help you learn!</p>
            <div className="d-flex flex-wrap gap-2 justify-content-center mt-3">
              {[
                "Explain the basics",
                "Give me an example",
                "Help with homework",
                "Practice problems"
              ].map((suggestion, index) => (
                <button
                  key={index}
                  className="btn btn-outline-primary btn-sm"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`mb-3 d-flex ${message.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
              >
                <div
                  className={`card ${
                    message.role === 'user' 
                      ? 'bg-primary text-white' 
                      : message.error 
                        ? 'bg-danger text-white'
                        : 'bg-light'
                  }`}
                  style={{ maxWidth: '75%' }}
                >
                  <div className="card-body py-2 px-3">
                    {message.role === 'assistant' && (
                      <div className="d-flex align-items-center mb-1">
                        <i className="fas fa-robot me-2"></i>
                        <small className="text-muted">AI Tutor</small>
                        {message.metadata?.context_used > 0 && (
                          <small className="text-muted ms-2">
                            <i className="fas fa-book me-1"></i>
                            {message.metadata.context_used} references
                          </small>
                        )}
                      </div>
                    )}
                    <div className="message-content">
                      {message.content.split('\n').map((line, lineIndex) => (
                        <div key={lineIndex}>{line}</div>
                      ))}
                    </div>
                    <small className={`d-block mt-1 ${message.role === 'user' ? 'text-light' : 'text-muted'}`}>
                      {formatTime(message.created_at)}
                    </small>
                  </div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="mb-3 d-flex justify-content-start">
                <div className="card bg-light" style={{ maxWidth: '75%' }}>
                  <div className="card-body py-2 px-3">
                    <div className="d-flex align-items-center">
                      <i className="fas fa-robot me-2"></i>
                      <div className="typing-indicator">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                      </div>
                      <small className="text-muted ms-2">AI is thinking...</small>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="px-3 py-2 border-top">
          <small className="text-muted">Suggested questions:</small>
          <div className="d-flex flex-wrap gap-1 mt-1">
            {suggestions.slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                className="btn btn-outline-secondary btn-sm"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message Input */}
      <div className="p-3 border-top">
        <div className="input-group">
          <textarea
            className="form-control"
            placeholder="Type your question here..."
            value={currentMessage}
            onChange={(e) => setCurrentMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            rows={2}
            disabled={isLoading}
            style={{ resize: 'none' }}
          />
          <button
            className="btn btn-primary"
            type="button"
            onClick={sendMessage}
            disabled={!currentMessage.trim() || isLoading}
          >
            {isLoading ? (
              <span className="spinner-border spinner-border-sm"></span>
            ) : (
              <i className="fas fa-paper-plane"></i>
            )}
          </button>
        </div>
        <small className="text-muted">
          Press Enter to send, Shift+Enter for new line
        </small>
      </div>

      <style jsx>{`
        .typing-indicator {
          display: flex;
          gap: 4px;
        }
        
        .typing-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #6c757d;
          animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) {
          animation-delay: -0.32s;
        }
        
        .typing-dot:nth-child(2) {
          animation-delay: -0.16s;
        }
        
        @keyframes typing {
          0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
        
        .chat-messages {
          scroll-behavior: smooth;
        }
        
        .message-content {
          word-wrap: break-word;
          white-space: pre-wrap;
        }
      `}</style>
    </div>
  );
}
