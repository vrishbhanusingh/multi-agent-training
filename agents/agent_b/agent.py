import os
import pika
import time

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin')
AGENT_NAME = 'agent_b'

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)

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
        channel.start_consuming()
    except Exception as e:
        print(f"[{AGENT_NAME}] Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5) 