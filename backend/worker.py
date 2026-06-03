"""
Background Worker - Processes messages from Service Bus queue
This simulates backend processing: send email, save to DB, etc.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient

load_dotenv()

CONNECTION_STR = os.getenv("AZURE_SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = os.getenv("QUEUE_NAME")

# Simulated processing functions
async def send_email(to: str, subject: str, body: str):
    """Simulate sending email"""
    print(f"📧 Sending email to {to}")
    print(f"   Subject: {subject}")
    await asyncio.sleep(0.5)  # Simulate API call
    print("   ✅ Email sent!")


async def save_to_database(data: dict):
    """Simulate saving to database"""
    print(f"💾 Saving to database: {data}")
    await asyncio.sleep(0.3)
    print("   ✅ Saved!")


async def send_notification(user_id: str, message: str):
    """Simulate push notification"""
    print(f"🔔 Sending notification to user {user_id}: {message}")
    await asyncio.sleep(0.2)
    print("   ✅ Notification sent!")


async def process_message(message):
    """
    Main processing logic - customize this for your use case!
    """
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing message")
    print(f"{'='*60}")
    print(f"Message ID: {message.message_id}")
    print(f"Content: {str(message)}")

    # Get message properties
    props = message.application_properties or {}
    priority = props.get(b'priority', b'normal').decode() if b'priority' in props else 'normal'
    source = props.get(b'source', b'unknown').decode() if b'source' in props else 'unknown'

    print(f"Priority: {priority}")
    print(f"Source: {source}")

    # Example: Process based on message content
    content = str(message).lower()

    try:
        # Simulate different actions based on message content
        if "email" in content:
            await send_email("user@example.com", "Notification", str(message))
        elif "save" in content:
            await save_to_database({"message": str(message), "priority": priority})
        elif "notify" in content:
            await send_notification("user_123", str(message))
        else:
            # Default processing
            print("⚙️  Processing generic message...")
            await asyncio.sleep(0.5)
            print("   ✅ Processed!")

        print(f"{'='*60}\n")
        return True

    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return False


async def run_worker():
    """Main worker loop"""
    if not CONNECTION_STR:
        print("ERROR: Service Bus not configured")
        return

    print(f"🚀 Worker started - listening on queue: {QUEUE_NAME}")
    print("Waiting for messages... (Ctrl+C to stop)\n")

    servicebus_client = ServiceBusClient.from_connection_string(CONNECTION_STR)

    async with servicebus_client:
        receiver = servicebus_client.get_queue_receiver(queue_name=QUEUE_NAME)

        async with receiver:
            async for message in receiver:
                success = await process_message(message)

                if success:
                    await receiver.complete_message(message)
                else:
                    await receiver.abandon_message(message)


async def main():
    try:
        await run_worker()
    except KeyboardInterrupt:
        print("\n\n👋 Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
