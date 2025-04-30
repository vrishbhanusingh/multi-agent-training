# Import standard libraries for operating system interaction, time functions, threading, randomness, and date/time objects.
import os
# Import Pika, the Python client library for RabbitMQ.
import pika
import time
import threading
import random
import datetime
# Import JSON library for encoding/decoding message payloads.
import json
# Import custom functions for interacting with the Gemini LLM and processing messages.
from gemini_llm import process_message, ask_gemini  
# Import custom clients for interacting with Redis for agent state and memory.
from redis_state import StateClient
from redis_memory import MemoryClient

# --- Configuration ---

# Get RabbitMQ connection details from environment variables, using defaults if not set.
# Hostname or IP address of the RabbitMQ server.
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
# Port number for the RabbitMQ server (AMQP protocol).
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
# Username for RabbitMQ authentication.
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
# Password for RabbitMQ authentication.
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin')
# Define the unique name for this agent instance.
AGENT_NAME = 'agent_b' # Changed agent name

# --- Client Initialization ---

# Initialize the Redis client for managing this agent's persistent state.
state_client = StateClient(agent_id=AGENT_NAME)
# Initialize the Redis client for managing this agent's memory (conversation history, thoughts, etc.).
memory_client = MemoryClient(agent_id=AGENT_NAME)

# --- Environment Setup ---

# Store the current timestamp as an ISO-formatted string in an environment variable.
os.environ["TIMESTAMP"] = datetime.datetime.now().isoformat()
# Store the agent's name in an environment variable.
os.environ["AGENT_NAME"] = AGENT_NAME 

# --- RabbitMQ Connection Setup ---

# Create credentials object for authenticating with RabbitMQ.
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
# Define connection parameters for establishing a connection to RabbitMQ.
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)

# --- Background Message Sending Function ---

# This function runs in a separate thread to periodically send messages initiated by this agent.
# interval: How often (in seconds) this agent should initiate a message. Default is 135s (2 minutes 15 seconds) for Agent B.
def send_gemini_message_periodically(interval=135):
    # Loop indefinitely to continuously send messages.
    while True:
        # Initialize connection and channel variables for this sending attempt.
        sender_connection = None 
        sender_channel = None
        try:
            # --- Prepare Message ---
            # Get the current time for this specific message cycle.
            current_time_iso = datetime.datetime.now().isoformat()
            # Update the environment variable.
            os.environ["TIMESTAMP"] = current_time_iso

            # Randomly choose another agent to send the message to.
            # Agent B will target either Agent A or Agent C.
            target_agent = random.choice(['agent_a', 'agent_c'])

            # Retrieve the agent's current state from Redis (if any).
            agent_state = state_client.get_state() or {}
            # Retrieve the recent conversation context from Redis memory.
            conversation_context = memory_client.get_conversation_context(max_messages=3)

            # Construct the prompt for the Gemini LLM.
            # It includes system instructions, conversation context, and the task (generate a message).
            prompt = f"""
            You are {AGENT_NAME}, an AI agent in a multi-agent system. 
            
            {conversation_context}
            
            Based on any previous conversations above, generate a short, interesting message to send to {target_agent}. 
            Keep it under 100 characters.
            """
            
            # Call the Gemini LLM to generate the message content.
            message = ask_gemini(prompt, use_memory=True)
            
            # --- Update Agent Memory and State ---
            # Store a record of the outgoing message in this agent's memory.
            memory_client.store_message({
                "sender": AGENT_NAME,       
                "recipient": target_agent, 
                "content": message,        
                "sent_at": current_time_iso
            })
            
            # Update this agent's state in Redis.
            state_client.update_or_create({
                "last_activity": "sending_message",
                "last_message_sent": {
                    "to": target_agent,
                    "content": message,
                    "timestamp": current_time_iso
                }
            })
            
            # --- Establish Dedicated Connection for Sending ---
            print(f"[{AGENT_NAME} Sender Thread] Connecting...")
            sender_connection = pika.BlockingConnection(parameters)
            sender_channel = sender_connection.channel()
            sender_channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
            print(f"[{AGENT_NAME} Sender Thread] Connected.")
            # --- End connection setup ---

            # --- Publish Message ---
            # Create the JSON payload.
            payload = json.dumps({"sender": AGENT_NAME, "content": message})

            print(f"[{AGENT_NAME} Sender Thread] Publishing to {target_agent}...")
            # Publish the message using the dedicated channel.
            sender_channel.basic_publish(
                exchange='agent_communication',
                routing_key=target_agent,
                body=payload.encode()
            )
            print(f"[{AGENT_NAME}] Sent to {target_agent}: {message}")

        # --- Error Handling for Sender Thread ---
        except pika.exceptions.AMQPConnectionError as conn_err:
            print(f"[{AGENT_NAME} Sender Thread] Connection failed: {conn_err}. Will retry after sleep.")
        except Exception as e:
            print(f"[{AGENT_NAME} Sender Thread] Error: {e}")
        finally:
            # --- Ensure Connection Cleanup ---
            if sender_channel and sender_channel.is_open:
                try:
                    sender_channel.close()
                except Exception as ch_close_err:
                     print(f"[{AGENT_NAME} Sender Thread] Error closing channel: {ch_close_err}")
            if sender_connection and sender_connection.is_open:
                try:
                    sender_connection.close()
                except Exception as conn_close_err:
                     print(f"[{AGENT_NAME} Sender Thread] Error closing connection: {conn_close_err}")

        # --- Interval Sleep ---
        print(f"[{AGENT_NAME} Sender Thread] Sleeping for {interval} seconds...")
        time.sleep(interval)

# --- Main Agent Loop ---
while True:
    try:
        # --- Establish Main Receiving Connection ---
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
        queue_name = AGENT_NAME
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(exchange='agent_communication', queue=queue_name, routing_key=queue_name)

        # --- Rate Limiting Setup ---
        last_response_times = {} 
        MIN_RESPONSE_INTERVAL = 60 

        # --- Message Callback Function ---
        def callback(ch, method, properties, body):
            current_time_iso = datetime.datetime.now().isoformat()
            current_timestamp = datetime.datetime.now().timestamp() 
            os.environ["TIMESTAMP"] = current_time_iso

            # --- Decode Incoming Message ---
            try:
                data = json.loads(body.decode())
                actual_sender = data['sender']
                received_message = data['content']
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[{AGENT_NAME}] Error decoding message body: {e}. Body: {body[:100]}...")
                return

            print(f"[{AGENT_NAME}] Received from {actual_sender}: {received_message}")

            # --- Rate Limiting Check ---
            last_sent_to_sender = last_response_times.get(actual_sender)
            if last_sent_to_sender and (current_timestamp - last_sent_to_sender < MIN_RESPONSE_INTERVAL):
                print(f"[{AGENT_NAME}] Rate limiting response to {actual_sender}. Last response was < {MIN_RESPONSE_INTERVAL}s ago.")
                memory_client.store_message({ 
                     "sender": actual_sender, 
                     "recipient": AGENT_NAME, 
                     "content": received_message,
                     "received_at": current_time_iso 
                })
                return 
            # --- End Rate Limiting Check ---
            
            # --- Update State & Memory (if not rate-limited) ---
            state_client.update_or_create({
                "last_activity": "receiving_message",
                "last_message_received": {
                    "from": actual_sender, 
                    "content": received_message,
                    "timestamp": current_time_iso
                }
            })

            memory_client.store_message({ 
                 "sender": actual_sender, 
                 "recipient": AGENT_NAME, 
                 "content": received_message,
                 "received_at": current_time_iso 
            })
            
            # --- Process Message and Generate Response ---
            result = process_message(actual_sender, received_message) 
            thinking_part = result.get("thinking", "")
            response_part = result.get("response", "")
            
            print(f"[{AGENT_NAME}] Thinking: {thinking_part}")
            
            # --- Send Response ---
            if actual_sender != "broadcast" and response_part: 
                response_payload = json.dumps({"sender": AGENT_NAME, "content": response_part})
                channel.basic_publish(
                    exchange='agent_communication',
                    routing_key=actual_sender,   
                    body=response_payload.encode() 
                )
                print(f"[{AGENT_NAME}] Responded to {actual_sender}: {response_part}")

                # --- Update Rate Limiting Info ---
                last_response_times[actual_sender] = current_timestamp
                # --- End Update ---

                # --- Update Memory & State (after sending response) ---
                memory_client.store_message({
                    "sender": AGENT_NAME,        
                    "recipient": actual_sender,
                    "content": response_part,
                    "sent_at": current_time_iso
                })
                
                state_client.update_or_create({
                    "last_activity": "responding_to_message",
                    "last_response_sent": {
                        "to": actual_sender, 
                        "content": response_part,
                        "timestamp": current_time_iso
                    }
                })

        # --- Start Consuming Messages ---
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        print(f"[{AGENT_NAME}] Waiting for messages...")

        # --- Start Background Sender Thread ---
        # Pass the interval (135s for Agent B) as an argument.
        sender_thread = threading.Thread(target=send_gemini_message_periodically, args=(135,), daemon=True)
        sender_thread.start()

        # --- Begin Consuming ---
        channel.start_consuming()

    # --- Main Loop Error Handling ---
    except pika.exceptions.AMQPConnectionError as conn_err: 
        print(f"[{AGENT_NAME} Main Thread] Connection failed: {conn_err}. Retrying in 5 seconds...")
        time.sleep(5)
    except Exception as e: 
        print(f"[{AGENT_NAME} Main Thread] Error: {e}. Retrying in 5 seconds...")
        time.sleep(5) 