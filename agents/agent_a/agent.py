import os
import pika
import time
import threading
from transformers import pipeline
import random

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin')
AGENT_NAME = 'agent_a'

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)

# Load the LLM pipeline once at startup
llm_generator = pipeline('text-generation', model='distilgpt2')

def send_random_llm_message_periodically(channel, interval=30):
    while True:
        prompt = random.choice([
            "Hello, agent_b! Here is a random thought:",
            "Agent_b, did you know:",
            "Random message for agent_b:",
            "FYI agent_b:",
        ])
        llm_output = llm_generator(prompt, max_length=30, num_return_sequences=1)[0]['generated_text']
        message = llm_output.strip()
        channel.basic_publish(
            exchange='agent_communication',
            routing_key='agent_b',
            body=message.encode()
        )
        print(f"[{AGENT_NAME}] Sent to agent_b: {message}")
        time.sleep(interval)

while True:
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
        queue_name = AGENT_NAME
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(exchange='agent_communication', queue=queue_name, routing_key=queue_name)

        def callback(ch, method, properties, body):
            print(f"[{AGENT_NAME}] Received: {body.decode()}")

        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        print(f"[{AGENT_NAME}] Waiting for messages...")

        # Start background thread for periodic LLM message sending
        sender_thread = threading.Thread(target=send_random_llm_message_periodically, args=(channel, 30), daemon=True)
        sender_thread.start()

        channel.start_consuming()
    except Exception as e:
        print(f"[{AGENT_NAME}] Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5) 