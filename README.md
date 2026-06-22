# Azure Service Bus Lab

Learn how to use Azure Service Bus queues with Python and React.

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   React     │ ──▶  │  FastAPI    │ ──▶  │  Service    │
│   Frontend  │      │  Backend    │      │  Bus Queue  │
└─────────────┘      └─────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │   Worker    │
                                           │  (Process)  │
                                           └─────────────┘
```

**Flow:**
1. User sends message from React frontend
2. FastAPI backend receives request
3. Backend pushes message to Service Bus queue
4. Background worker picks up message and processes it

---
## Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- Azure Service Bus namespace and queue

### Step 1: Configure Environment

Edit `.env` file with your Azure credentials:
```
AZURE_SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://your-namespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=YOUR_KEY
QUEUE_NAME=your-queue-name
```
### Step 2: Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```
**Frontend:**
```bash
cd frontend
npm install
```
### Step 3: Run the Application

Open **3 separate terminals**:

| Terminal | Command | Purpose |
|----------|---------|---------|
| 1 | `cd backend && python -m uvicorn main:app --reload --port 8000` | API Server |
| 2 | `cd backend && python worker.py` | Message Processor |
| 3 | `cd frontend && npm run dev` | React Frontend |

### Step 4: Open in Browser

Go to: **http://localhost:5173**
---
## How to Test

### Send a Message
1. Open the React frontend (http://localhost:5173)
2. Type a message in the text area
3. Select priority (Low/Normal/High)
4. Click "Send to Queue"

### Watch Processing
Look at **Terminal 2 (Worker)** to see real-time processing:
```
==================================================
[09:07:11] Processing message
Message ID: 1d538cf3-cdba-4f21-b019-4521ea5f8b67
Content: hello
Priority: normal
Source: react_frontend
 Processing generic message...
   ✅ Processed!
==================================================
```
### Check Azure Portal
- Go to Azure Portal → Service Bus → Queue
- **Message count shows 0** because worker processes messages instantly

### See Messages in Queue
To see messages waiting in the queue:
1. **Stop the worker** (Ctrl+C in Terminal 2)
2. Send a message from frontend
3. Check Azure Portal → **Active messages: 1**
4. Restart worker to process it

---

## Quick Actions

Try these message prefixes to see different processing:

| Message | Worker Action |
|---------|---------------|
| `email: Welcome!` | Simulates sending email |
| `save: User data` | Simulates database save |
| `notify: New message!` | Simulates push notification |
| Any other text | Generic processing |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status |
| GET | `/api/status` | Check Service Bus connection |
| POST | `/api/send` | Send message to queue |

---
## Troubleshooting

### "uvicorn not recognized"
Run with: `python -m uvicorn main:app --reload --port 8000`

### "Module not found"
Install dependencies: `pip install -r requirements.txt`

### "CORS error"
Make sure backend is running on port 8000

### Messages disappear from queue
This is normal! The worker processes messages immediately. Stop the worker to see messages accumulate.
---
## Project Structure
```
azure_service_bus_lab/
├── backend/
│   ├── main.py          # FastAPI endpoints
│   ├── worker.py        # Background message processor
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # Main React component
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
├── .env                 # Your Azure credentials
└── README.md
```
