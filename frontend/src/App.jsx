import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

function App() {
  const [message, setMessage] = useState('')
  const [priority, setPriority] = useState('normal')
  const [status, setStatus] = useState({ configured: false, queue: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])

  // Check backend status on mount
  useEffect(() => {
    axios.get(`${API_URL}/api/status`)
      .then(res => setStatus(res.data))
      .catch(() => setStatus({ configured: false, queue: 'Not connected' }))
  }, [])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!message.trim()) return

    setLoading(true)
    setResult(null)

    try {
      const response = await axios.post(`${API_URL}/api/send`, {
        content: message,
        priority: priority
      })

      setResult({ type: 'success', text: response.data.message })
      setHistory(prev => [
        { message, priority, time: new Date().toLocaleTimeString() },
        ...prev.slice(0, 9)
      ])
      setMessage('')
    } catch (error) {
      setResult({ type: 'error', text: error.response?.data?.detail || 'Failed to send message' })
    } finally {
      setLoading(false)
    }
  }

  const quickActions = [
    { text: 'email: Welcome to our service!', label: 'Send Email' },
    { text: 'save: User registration data', label: 'Save to DB' },
    { text: 'notify: You have a new message', label: 'Push Notification' },
  ]

  return (
    <div className="container">
      <h1>🚌 Azure Service Bus</h1>
      <p className="subtitle">React Frontend + FastAPI Backend Demo</p>

      {/* Architecture Overview */}
      <div className="architecture">
        <div className="arch-box">
          <h4>⚛️ Frontend</h4>
          <p>React sends messages via API</p>
        </div>
        <div className="arrow">→</div>
        <div className="arch-box">
          <h4>🚌 Service Bus</h4>
          <p>Queue stores messages</p>
        </div>
        <div className="arrow">→</div>
        <div className="arch-box">
          <h4>⚙️ Worker</h4>
          <p>Processes messages</p>
        </div>
      </div>

      {/* Status */}
      <div className="card" style={{ marginTop: '30px' }}>
        <div className="status">
          <div className={`status-dot ${status.configured ? 'connected' : 'disconnected'}`} />
          <span>
            {status.configured 
              ? `Connected to queue: ${status.queue}` 
              : 'Backend not connected'}
          </span>
        </div>

        {/* Send Message Form */}
        <form onSubmit={sendMessage}>
          <div className="form-group">
            <label>Message Content</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message here... (try starting with 'email:', 'save:', or 'notify:')"
            />
          </div>

          <div className="form-group">
            <label>Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>

          <button type="submit" disabled={loading || !status.configured}>
            {loading ? 'Sending...' : 'Send to Queue'}
          </button>
        </form>

        {/* Quick Actions */}
        <div style={{ marginTop: '20px' }}>
          <label style={{ marginBottom: '10px', display: 'block' }}>Quick Actions:</label>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {quickActions.map((action, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setMessage(action.text)}
                style={{ 
                  background: 'rgba(255,255,255,0.1)', 
                  padding: '8px 16px',
                  fontSize: '14px'
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Result Message */}
        {result && (
          <div className={`message ${result.type}`}>
            {result.text}
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div className="history">
            <h3>📤 Sent Messages</h3>
            <div className="history-list">
              {history.map((item, i) => (
                <div key={i} className="history-item">
                  <span className="history-time">{item.time}</span>
                  <span style={{ marginLeft: '10px' }}>[{item.priority}]</span>
                  <div>{item.message}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
