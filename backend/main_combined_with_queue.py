"""
Combined FastAPI + Worker in ONE service
Option 2: Background Thread Polling Service Bus Queue
This checks the queue every few seconds automatically!
"""

import asyncio
import threading
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from datetime import datetime
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

load_dotenv()

CONNECTION_STR = os.getenv("AZURE_SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = os.getenv("QUEUE_NAME")

app = FastAPI(title="Azure Service Bus - Combined with Queue Polling")

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


# ============================================
# MESSAGE PROCESSING FUNCTIONS
# ============================================

async def process_message(content: str, priority: str, source: str = "unknown"):
    """Process message - customize this for your needs!"""
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing Message")
    print(f"Source: {source}")
    print(f"Content: {content}")
    print(f"Priority: {priority}")
    
    # Simulate different actions based on content
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


# ============================================
# BACKGROUND THREAD - POLLS QUEUE EVERY FEW SECONDS
# ============================================

async def worker_loop():
    """
    This runs continuously in background thread.
    Checks Service Bus queue for new messages.
    """
    if not CONNECTION_STR:
        print("❌ No connection string - worker disabled")
        return

    print(f"🚀 Worker started - polling queue: {QUEUE_NAME}")
    print("   Checking for messages every few seconds...\n")

    servicebus_client = ServiceBusClient.from_connection_string(CONNECTION_STR)

    async with servicebus_client:
        receiver = servicebus_client.get_queue_receiver(queue_name=QUEUE_NAME)

        async with receiver:
            # This loop runs forever, checking for messages
            async for message in receiver:
                try:
                    # Get message content
                    content = str(message)
                    
                    # Get properties
                    props = message.application_properties or {}
                    priority = props.get(b'priority', b'normal').decode() if b'priority' in props else 'normal'
                    source = props.get(b'source', b'unknown').decode() if b'source' in props else 'queue_poller'

                    # Process the message
                    await process_message(content, priority, source)

                    # Mark as complete (removes from queue)
                    await receiver.complete_message(message)

                except Exception as e:
                    print(f"❌ Error: {e}")
                    await receiver.abandon_message(message)


def run_worker_thread():
    """Run the async worker loop in a thread"""
    asyncio.run(worker_loop())


# ============================================
# FASTAPI ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "status": "running",
        "mode": "combined_with_queue_polling",
        "queue": QUEUE_NAME
    }


@app.get("/api/status")
async def get_status():
    """Check if API is running"""
    return {
        "configured": CONNECTION_STR is not None,
        "queue": QUEUE_NAME,
        "mode": "combined_with_queue_polling"
    }


@app.post("/api/send")
async def send_message(request: MessageRequest):
    """
    Send message to Service Bus queue.
    The background worker will pick it up and process.
    """
    if not CONNECTION_STR:
        raise HTTPException(status_code=500, detail="Service Bus not configured")

    servicebus_client = ServiceBusClient.from_connection_string(CONNECTION_STR)

    async with servicebus_client:
        sender = servicebus_client.get_queue_sender(queue_name=QUEUE_NAME)

        async with sender:
            message = ServiceBusMessage(request.content)
            message.application_properties = {
                "priority": request.priority,
                "source": "react_frontend"
            }

            await sender.send_messages(message)

            return {
                "success": True,
                "message": "Message sent to queue",
                "message_id": message.message_id,
                "note": "Background worker will process it automatically"
            }


# ============================================
# STARTUP - LAUNCH BACKGROUND WORKER THREAD
# ============================================

@app.on_event("startup")
async def startup_event():
    """
    When FastAPI starts, launch background thread.
    This thread polls Service Bus queue continuously.
    """
    worker_thread = threading.Thread(target=run_worker_thread, daemon=True)
    worker_thread.start()
    print("✅ Background queue poller started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
