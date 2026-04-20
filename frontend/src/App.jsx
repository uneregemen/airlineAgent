import React, { useState, useRef, useEffect } from 'react';
import './App.css';

// ─── Helper: Format time ───
function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ─── Helper: Generate conversation ID ───
function generateId() {
  return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

// ─── Flight Card Component ───
function FlightCard({ flight, onBook }) {
  const seats = flight.availableSeats || 0;
  const departure = flight.departure ? new Date(flight.departure) : null;
  const arrival = flight.arrival ? new Date(flight.arrival) : null;

  return (
    <div className="flight-card">
      <div className="flight-card-header">
        <span className="flight-number">{flight.flightNumber}</span>
        <span className={`flight-seats ${seats < 5 ? 'low' : ''}`}>
          {seats} seats
        </span>
      </div>
      <div className="flight-route">
        <div>
          <span className="flight-airport-code">{flight.from}</span>
          <span className="flight-airport-name">
            {departure ? formatTime(departure) : ''}
          </span>
        </div>
        <div className="flight-route-line">
          <span className="route-plane">✈</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span className="flight-airport-code">{flight.to}</span>
          <span className="flight-airport-name">
            {arrival ? formatTime(arrival) : ''}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Status Badge Component ───
function StatusBadge({ status, message }) {
  const isSuccess = status?.toLowerCase() === 'success';
  return (
    <div className={`status-badge ${isSuccess ? 'success' : 'error'}`}>
      {isSuccess ? '✅' : '❌'} {message || status}
    </div>
  );
}

// ─── Tool Result Component ───
function ToolResult({ data, onAction }) {
  if (!data || !data._tool) return null;

  // Flight search results
  if (data._tool === 'search_flights' && data.flights && data.flights.length > 0) {
    return (
      <div>
        <div className="flight-cards">
          {data.flights.map((f, i) => (
            <FlightCard key={i} flight={f} />
          ))}
        </div>
        <div className="inline-actions">
          <button className="inline-action-btn" onClick={() => onAction('book')}>
            ＋ Book Flight
          </button>
          <button className="inline-action-btn" onClick={() => onAction('search')}>
            🔍 Query Flight
          </button>
        </div>
      </div>
    );
  }

  // Booking result
  if (data._tool === 'book_flight' && data.status) {
    const isSuccess = data.status.toLowerCase() === 'success';
    return (
      <div>
        {isSuccess ? (
          <div className="booking-card">
            <div className="booking-card-title">✅ Flight Booked Successfully!</div>
            <div className="booking-route">
              <div className="booking-airport">
                <div className="booking-code">{data.flight_number || 'N/A'}</div>
              </div>
            </div>
            <div className="booking-details">
              <div className="booking-detail-row">👤 {data.passenger || 'Passenger'}</div>
              <div className="booking-detail-row">📅 {data.date || 'Date'}</div>
              {data.message && <div className="booking-detail-row">🎫 {data.message}</div>}
            </div>
          </div>
        ) : (
          <StatusBadge status={data.status} message={data.message} />
        )}
        <div className="inline-actions">
          <button className="inline-action-btn" onClick={() => onAction('checkin')}>
            ☑ Check In
          </button>
          <button className="inline-action-btn" onClick={() => onAction('search')}>
            🔍 Query Flight
          </button>
        </div>
      </div>
    );
  }

  // Check-in / Cancel / Get Ticket results
  if (['check_in', 'cancel_ticket', 'get_ticket'].includes(data._tool)) {
    return (
      <div>
        <StatusBadge status={data.status} message={data.message} />
        {data._tool === 'check_in' && data.status?.toLowerCase() === 'success' && (
          <div className="booking-card" style={{ marginTop: '8px' }}>
            <div className="booking-card-title">🎫 Boarding Pass</div>
            <div className="booking-details">
              <div className="booking-detail-row">✈ {data.flight_number || ''}</div>
              <div className="booking-detail-row">👤 {data.passenger || ''}</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}

// ─── Main App ───
function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId] = useState(generateId());
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // ─── Send Message ───
  const sendMessage = async (text = null) => {
    const msg = text || input.trim();
    if (!msg || loading) return;

    const userMessage = {
      sender: 'user',
      text: msg,
      time: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          conversation_id: conversationId,
        }),
      });

      const data = await response.json();

      const botMessage = {
        sender: 'bot',
        text: data.response || 'No response received.',
        time: new Date().toISOString(),
        toolCalls: data.tool_calls || [],
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Connection Error:', error);
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: '⚠️ Could not connect to the AI agent. Make sure the backend is running on port 8000.',
        time: new Date().toISOString(),
        toolCalls: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  // ─── Inline Action Handler ───
  const handleInlineAction = (action) => {
    if (action === 'search') {
      setInput('Show me flights from IST to ');
      inputRef.current?.focus();
    } else if (action === 'book') {
      setInput('Book flight ');
      inputRef.current?.focus();
    } else if (action === 'checkin') {
      setInput('Check in for flight ');
      inputRef.current?.focus();
    }
  };

  // ─── Key Handler ───
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ─── New Chat ───
  const handleNewChat = () => {
    setMessages([]);
    fetch(`http://127.0.0.1:8000/conversations/${conversationId}`, { method: 'DELETE' }).catch(() => {});
  };

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="header-avatar">✈️</div>
          <div>
            <div className="chat-header-title">AI Agent - Flight Actions</div>
            <div className="chat-header-subtitle">Powered by Ollama LLM</div>
          </div>
        </div>
        <div className="header-actions">
          <button className="header-btn" onClick={handleNewChat} title="New chat" id="new-chat-btn">
            ↻
          </button>
        </div>
      </header>

      {/* ── Messages ── */}
      <div className="messages-container" id="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <div className="welcome-avatar">✈️</div>
            <h1 className="welcome-title">Hello! How can I assist you?</h1>
            <p className="welcome-subtitle">
              Search flights, book tickets, or check in — just ask!
            </p>
            <div className="quick-actions">
              <button
                className="quick-action-btn"
                onClick={() => sendMessage('Show me flights from IST to FRA')}
                id="action-search"
              >
                <div className="action-icon search">🔍</div>
                <div>
                  <div className="action-label">Query Flight</div>
                  <div className="action-desc">Search available flights</div>
                </div>
              </button>
              <button
                className="quick-action-btn"
                onClick={() => sendMessage('Book flight TK1523 for Egemen Uner on 2026-05-10')}
                id="action-book"
              >
                <div className="action-icon book">＋</div>
                <div>
                  <div className="action-label">Book Flight</div>
                  <div className="action-desc">Purchase a ticket</div>
                </div>
              </button>
              <button
                className="quick-action-btn"
                onClick={() => sendMessage('Check in for flight TK1523 on 2026-05-10 for Egemen Uner')}
                id="action-checkin"
              >
                <div className="action-icon checkin">☑</div>
                <div>
                  <div className="action-label">Check In</div>
                  <div className="action-desc">Get your boarding pass</div>
                </div>
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div key={index} className={`message-row ${msg.sender}`}>
                <div className={`message-avatar ${msg.sender}`}>
                  {msg.sender === 'bot' ? '✈' : '👤'}
                </div>
                <div className="message-content">
                  <div className="message-bubble">{msg.text}</div>

                  {/* Tool Results */}
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div>
                      {msg.toolCalls.map((tc, i) => (
                        <ToolResult key={i} data={tc} onAction={handleInlineAction} />
                      ))}
                    </div>
                  )}

                  <span className="message-time">
                    {msg.time ? formatTime(new Date(msg.time)) : ''}
                  </span>
                </div>
              </div>
            ))}
          </>
        )}

        {/* Typing Indicator */}
        {loading && (
          <div className="typing-indicator">
            <div className="message-avatar bot">✈</div>
            <div className="typing-bubble">
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input Area ── */}
      <div className="input-area">
        <div className="input-wrapper">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="What can I assist you with?"
            disabled={loading}
            id="chat-input"
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            id="send-button"
          >
            ➤
          </button>
        </div>
        <div className="input-hint">
          MCP → API Gateway → Airline API
        </div>
      </div>
    </div>
  );
}

export default App;