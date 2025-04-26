import pika
import os

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin')

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)

for agent in ['agent_a', 'agent_b', 'agent_c']:
    message = f"Hello {agent}! This is a test message from the testing agent."
    channel.basic_publish(
        exchange='agent_communication',
        routing_key=agent,
        body=message.encode()
    )
    print(f"Sent to {agent}: {message}")

connection.close() 