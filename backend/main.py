"""
FastAPI Backend for Azure Service Bus
Frontend sends messages via API, backend pushes to Service Bus queue
"""

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

load_dotenv()

CONNECTION_STR = os.getenv("AZURE_SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = os.getenv("QUEUE_NAME")

app = FastAPI(title="Azure Service Bus API")

# Enable CORS for React frontend
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


class MessageResponse(BaseModel):
    success: bool
    message: str
    message_id: str = None


@app.get("/")
async def root():
    return {"status": "running", "service": "Azure Service Bus API"}


@app.post("/api/send", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """
    Receive message from frontend, send to Service Bus queue
    A background worker will process this message later
    """
    if not CONNECTION_STR:
        raise HTTPException(status_code=500, detail="Service Bus not configured")

    try:
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

                return MessageResponse(
                    success=True,
                    message="Message sent to queue successfully",
                    message_id=message.message_id
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Check if Service Bus is configured"""
    return {
        "configured": CONNECTION_STR is not None,
        "queue": QUEUE_NAME
    }
