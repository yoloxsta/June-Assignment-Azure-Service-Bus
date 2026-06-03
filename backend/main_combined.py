"""
Combined FastAPI + Worker in ONE service
Option 1: Using BackgroundTasks (processes after HTTP response)
"""

import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

app = FastAPI(title="Azure Service Bus - Combined API + Worker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    content: str
    priority: str = "normal"


# Simulated processing functions
async def process_message_task(content: str, priority: str):
    """
    This runs in background AFTER the HTTP response is sent.
    User gets immediate response, processing happens async.
    """
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Background Processing")
    print(f"Content: {content}")
    print(f"Priority: {priority}")
    
    # Simulate different actions
    if "email" in content.lower():
        print("📧 Sending email...")
        await asyncio.sleep(0.5)
        print("   ✅ Email sent!")
    elif "save" in content.lower():
        print("💾 Saving to database...")
        await asyncio.sleep(0.3)
        print("   ✅ Saved!")
    elif "notify" in content.lower():
        print("🔔 Sending notification...")
        await asyncio.sleep(0.2)
        print("   ✅ Notification sent!")
    else:
        print("⚙️  Processing...")
        await asyncio.sleep(0.5)
        print("   ✅ Done!")
    
    print(f"{'='*50}\n")


@app.get("/")
async def root():
    return {"status": "running", "mode": "combined"}


@app.get("/api/status")
async def get_status():
    """Check if API is running"""
    return {
        "configured": True,
        "queue": os.getenv("QUEUE_NAME", "not-set"),
        "mode": "combined"
    }


@app.post("/api/send")
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Receive message, return immediately, process in background.
    
    Flow:
    1. API receives request
    2. Queues background task
    3. Returns response immediately (user doesn't wait)
    4. Background task processes message
    """
    # Add task to background queue
    background_tasks.add_task(
        process_message_task, 
        request.content, 
        request.priority
    )
    
    return {
        "success": True,
        "message": "Message queued for processing",
        "note": "Check server logs to see background processing"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
