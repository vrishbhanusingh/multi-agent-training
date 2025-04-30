import os
import time
import pika
import docker

def test_agent_b_receives_message():
    """
    Integration test: Send a test message to agent_b via RabbitMQ and check agent_b's logs for receipt.
    Assumes agent_b is already running as a container (via Docker Compose).
    """
    # Send a test message to agent_b
    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", 5672))
    rabbitmq_user = os.environ.get("RABBITMQ_USER", "admin")
    rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "admin")
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    parameters = pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
    test_message = "pytest-integration-message"
    channel.basic_publish(
        exchange='agent_communication',
        routing_key='agent_b',
        body=test_message.encode()
    )
    connection.close()

    # Wait briefly for agent_b to process the message
    time.sleep(2)

    # Use docker SDK to get agent_b logs
    client = docker.from_env()
    container = client.containers.get("agent_b")
    logs = container.logs(tail=100).decode()
    assert test_message in logs, f"agent_b did not receive the test message. Logs:\n{logs}"