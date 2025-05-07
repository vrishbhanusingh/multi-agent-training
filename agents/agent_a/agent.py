# Import standard libraries for operating system interaction, time functions, threading, randomness, and date/time objects.
import os
# Import Pika, the Python client library for RabbitMQ.
import pika
import time
import threading
import random   
import datetime
# Import Protocol Buffers generated code for A2A messaging.
from common.a2a_protocol.proto import a2a_message_pb2
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
AGENT_NAME = 'agent_a'

# --- Client Initialization ---

# Initialize the Redis client for managing this agent's persistent state.
state_client = StateClient(agent_id=AGENT_NAME)
# Initialize the Redis client for managing this agent's memory (conversation history, thoughts, etc.).
memory_client = MemoryClient(agent_id=AGENT_NAME)

# --- Environment Setup ---

# Store the current timestamp as an ISO-formatted string in an environment variable. 
# This allows other modules (like gemini_llm) potentially loaded later to access a consistent timestamp.
os.environ["TIMESTAMP"] = datetime.datetime.now().isoformat()
# Store the agent's name in an environment variable, primarily for the sender thread to know its identity.
os.environ["AGENT_NAME"] = AGENT_NAME 

# --- RabbitMQ Connection Setup ---

# Create credentials object for authenticating with RabbitMQ.
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
# Define connection parameters for establishing a connection to RabbitMQ.
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)

# --- Background Message Sending Function ---

# This function runs in a separate thread to periodically send messages initiated by this agent.
# It now manages its own RabbitMQ connection to avoid threading issues with the main consumer connection.
# interval: How often (in seconds) this agent should initiate a message. Default is 120s (2 minutes).
def send_gemini_message_periodically(interval=120):
    # Loop indefinitely to continuously send messages.
    while True:
        # Initialize connection and channel variables for this sending attempt.
        # Defined outside 'try' to ensure they are accessible in the 'finally' block for cleanup.
        sender_connection = None 
        sender_channel = None
        try:
            # --- Prepare Message ---
            # Get the current time for this specific message cycle.
            current_time_iso = datetime.datetime.now().isoformat()
            # Update the environment variable (optional, but maintains consistency if other parts rely on it).
            os.environ["TIMESTAMP"] = current_time_iso

            # Randomly choose another agent to send the message to.
            # Agent A will target either Agent B or Agent C.
            target_agent = random.choice(['agent_b', 'agent_c'])

            # Retrieve the agent's current state from Redis (if any). Defaults to an empty dict.
            agent_state = state_client.get_state() or {}
            # Retrieve the recent conversation context (last 3 messages) from Redis memory.
            conversation_context = memory_client.get_conversation_context(max_messages=3)

            # Construct the prompt for the Gemini LLM.
            # It includes system instructions, conversation context, and the task (generate a message).
            prompt = f"""
            You are {AGENT_NAME}, an AI agent in a multi-agent system. 
            
            {conversation_context}
            
            Based on any previous conversations above, generate a short, interesting message to send to {target_agent}. 
            Keep it under 100 characters.
            """
            
            # Call the Gemini LLM to generate the message content, potentially using memory context.
            message = ask_gemini(prompt, use_memory=True)
            
            # --- Update Agent Memory and State ---
            # Store a record of the outgoing message in this agent's memory (Redis).
            memory_client.store_message({
                "sender": AGENT_NAME,        # This agent is the sender.
                "recipient": target_agent,  # The agent being sent to.
                "content": message,         # The generated message content.
                "sent_at": current_time_iso # Timestamp when the message was prepared to be sent.
            })
            
            # Update this agent's state in Redis to reflect the latest activity.
            state_client.update_or_create({
                "last_activity": "sending_message", # Indicate the type of activity.
                "last_message_sent": {              # Details about the message sent.
                    "to": target_agent,
                    "content": message,
                    "timestamp": current_time_iso
                }
            })
            
            # --- Establish Dedicated Connection for Sending ---
            # Log that the sender thread is attempting to connect.
            print(f"[{AGENT_NAME} Sender Thread] Connecting...") 
            # Create a new, independent connection to RabbitMQ specifically for this send operation.
            sender_connection = pika.BlockingConnection(parameters)
            # Open a channel on this dedicated connection.
            sender_channel = sender_connection.channel()
            # Declare the exchange (ensures it exists). This is idempotent.
            sender_channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
            # Log successful connection.
            print(f"[{AGENT_NAME} Sender Thread] Connected.") 
            # --- End connection setup ---

            # --- Publish Protobuf Message ---
            # Construct the A2AMessage protobuf object (see a2a_message.proto for field definitions).
            message_obj = a2a_message_pb2.A2AMessage(
                sender=AGENT_NAME,
                recipient=target_agent,
                content=message,
                sent_at=current_time_iso
            )
            # Serialize the protobuf message to bytes for transmission.
            payload_bytes = message_obj.SerializeToString()

            print(f"[{AGENT_NAME} Sender Thread] Publishing protobuf message to {target_agent}...")
            sender_channel.basic_publish(
                exchange='agent_communication',
                routing_key=target_agent,
                body=payload_bytes
            )
            print(f"[{AGENT_NAME}] Sent protobuf message to {target_agent}: {message_obj.content}")

        except pika.exceptions.AMQPConnectionError as conn_err:
            print(f"[{AGENT_NAME} Sender Thread] Connection failed: {conn_err}. Will retry after sleep.")
        except Exception as e:
            print(f"[{AGENT_NAME} Sender Thread] Error: {e}")
        finally:
            # --- Ensure Connection Cleanup ---
            # This block executes whether the 'try' succeeded or failed.
            # Check if the channel was opened and is still open.
            if sender_channel and sender_channel.is_open:
                try:
                    # Attempt to close the channel.
                    sender_channel.close()
                except Exception as ch_close_err:
                     # Log if closing the channel fails.
                     print(f"[{AGENT_NAME} Sender Thread] Error closing channel: {ch_close_err}")
            # Check if the connection was established and is still open.
            if sender_connection and sender_connection.is_open:
                try:
                    # Attempt to close the connection.
                    sender_connection.close()
                except Exception as conn_close_err:
                     # Log if closing the connection fails.
                     print(f"[{AGENT_NAME} Sender Thread] Error closing connection: {conn_close_err}")

        # --- Interval Sleep ---
        # Pause the sender thread for the specified interval before the next cycle.
        # This happens regardless of whether the message sending was successful or not.
        print(f"[{AGENT_NAME} Sender Thread] Sleeping for {interval} seconds...") 
        time.sleep(interval)

# --- Main Agent Loop ---
# This loop attempts to establish and maintain the primary connection for receiving messages.
while True:
    try:
        # --- Establish Main Receiving Connection ---
        # Create the main blocking connection to RabbitMQ for consuming messages.
        connection = pika.BlockingConnection(parameters)
        # Open a channel on this main connection.
        channel = connection.channel()
        # Declare the exchange (ensures it exists).
        channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
        # Define the queue name for this agent (same as the agent's name).
        queue_name = AGENT_NAME
        # Declare the agent's queue. 'durable=True' means the queue survives broker restarts.
        channel.queue_declare(queue=queue_name, durable=True)
        # Bind the agent's queue to the exchange using its own name as the routing key.
        # This means messages published with this agent's name as the routing key will arrive here.
        channel.queue_bind(exchange='agent_communication', queue=queue_name, routing_key=queue_name)

        # --- Rate Limiting Setup ---
        # Initialize a dictionary to store the last time a response was sent TO a specific sender.
        # This is kept within the connection loop scope, resetting if the main connection drops.
        last_response_times = {} 
        # Define the minimum number of seconds required between responses to the same sender.
        MIN_RESPONSE_INTERVAL = 60 

        # --- Message Callback Function ---
        # This function is executed whenever a message arrives in the agent's queue.
        # ch: The channel object.
        # method: Contains delivery information (like routing key, delivery tag).
        # properties: Message properties (headers, content type, etc.).
        # body: The raw message content (as bytes).
        def callback(ch, method, properties, body):
            # Get current timestamps for logging and calculations.
            current_time_iso = datetime.datetime.now().isoformat()
            current_timestamp = datetime.datetime.now().timestamp() 
            # Update environment variable (mainly for consistency).
            os.environ["TIMESTAMP"] = current_time_iso

            # --- Decode Incoming Protobuf Message ---
            try:
                # Parse the incoming bytes as an A2AMessage protobuf object.
                msg = a2a_message_pb2.A2AMessage()
                msg.ParseFromString(body)
                actual_sender = msg.sender
                received_message = msg.content
            except Exception as e:
                print(f"[{AGENT_NAME}] Error decoding protobuf message: {e}. Raw body: {body[:100]}...")
                return

            print(f"[{AGENT_NAME}] Received protobuf message from {actual_sender}: {received_message}")

            # --- Rate Limiting Check ---
            # Get the timestamp when we last responded to this specific 'actual_sender'.
            last_sent_to_sender = last_response_times.get(actual_sender)
            # Check if a previous response exists and if it was sent too recently.
            if last_sent_to_sender and (current_timestamp - last_sent_to_sender < MIN_RESPONSE_INTERVAL):
                # Log that the response is being rate-limited.
                print(f"[{AGENT_NAME}] Rate limiting response to {actual_sender}. Last response was < {MIN_RESPONSE_INTERVAL}s ago.") 
                # Optionally: Store the received message in memory even if not responding.
                memory_client.store_message({ 
                     "sender": actual_sender, 
                     "recipient": AGENT_NAME, 
                     "content": received_message,
                     "received_at": current_time_iso 
                })
                # Stop processing this message; do not generate or send a response.
                return 
            # --- End Rate Limiting Check ---
            
            # --- Update State & Memory (if not rate-limited) ---
            # Update this agent's state in Redis to record receiving this message.
            state_client.update_or_create({
                "last_activity": "receiving_message",
                "last_message_received": {
                    "from": actual_sender, # Log the correct sender.
                    "content": received_message,
                    "timestamp": current_time_iso
                }
            })

            # Store the received message in this agent's memory (Redis).
            # This might be redundant if logged during the rate limit check, consider removing one.
            memory_client.store_message({ 
                 "sender": actual_sender, 
                 "recipient": AGENT_NAME, 
                 "content": received_message,
                 "received_at": current_time_iso 
            })
            
            # --- Process Message and Generate Response ---
            # Call the 'process_message' function (likely involving an LLM call) 
            # ONLY if the rate limit was not hit. Pass the correct sender.
            result = process_message(actual_sender, received_message) 
            # Extract the thinking process and response content from the result.
            thinking_part = result.get("thinking", "")
            response_part = result.get("response", "")
            
            # Log the thinking process generated by 'process_message'.
            print(f"[{AGENT_NAME}] Thinking: {thinking_part}")
            
            # --- Send Response ---
            # Check if the sender wasn't a broadcast message and if a response was generated.
            if actual_sender != "broadcast" and response_part:
                # Construct a protobuf response message.
                response_msg = a2a_message_pb2.A2AMessage(
                    sender=AGENT_NAME,
                    recipient=actual_sender,
                    content=response_part,
                    sent_at=current_time_iso
                )
                # Serialize and send the response as protobuf bytes.
                channel.basic_publish(
                    exchange='agent_communication',
                    routing_key=actual_sender,
                    body=response_msg.SerializeToString()
                )
                print(f"[{AGENT_NAME}] Responded to {actual_sender} with protobuf: {response_part}")

                # --- Update Rate Limiting Info ---
                # Record the timestamp of this response TO the specific actual_sender.
                last_response_times[actual_sender] = current_timestamp
                # --- End Update ---

                # --- Update Memory & State (after sending response) ---
                # Store a record of the sent response in this agent's memory.
                memory_client.store_message({
                    "sender": AGENT_NAME,         # This agent sent the response.
                    "recipient": actual_sender, # The original sender is the recipient.
                    "content": response_part,
                    "sent_at": current_time_iso
                })
                
                # Update this agent's state to reflect sending the response.
                state_client.update_or_create({
                    "last_activity": "responding_to_message",
                    "last_response_sent": {
                        "to": actual_sender, # Log the correct recipient.
                        "content": response_part,
                        "timestamp": current_time_iso
                    }
                })

        # --- Start Consuming Messages ---
        # Register the 'callback' function to handle messages arriving in the queue.
        # auto_ack=True: Automatically acknowledge messages upon receipt (simplifies code, but risk of message loss if agent crashes during processing).
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        # Log that the agent is ready to receive messages.
        print(f"[{AGENT_NAME}] Waiting for messages...")

        # --- Start Background Sender Thread ---
        # Create and start the background thread that runs the 'send_gemini_message_periodically' function.
        # Pass the interval (120s for Agent A) as an argument.
        # daemon=True: Allows the main program to exit even if this thread is still running.
        sender_thread = threading.Thread(target=send_gemini_message_periodically, args=(120,), daemon=True)
        sender_thread.start()

        # --- Begin Consuming ---
        # Start the main blocking loop that waits for and processes incoming messages via the callback.
        # This line will block until the connection is lost or the process is interrupted.
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as conn_err: 
        print(f"[{AGENT_NAME} Main Thread] Connection failed: {conn_err}. Retrying in 5 seconds...")
        time.sleep(5)
    except Exception as e: 
        print(f"[{AGENT_NAME} Main Thread] Error: {e}. Retrying in 5 seconds...")
        time.sleep(5) 