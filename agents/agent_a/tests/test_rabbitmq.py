import os
import pika
import pytest
import time

def get_rabbitmq_params():
    return dict(
        host=os.environ.get("RABBITMQ_HOST", "localhost"),
        port=int(os.environ.get("RABBITMQ_PORT", 5672)),
        credentials=pika.PlainCredentials(
            os.environ.get("RABBITMQ_USER", "admin"),
            os.environ.get("RABBITMQ_PASSWORD", "admin"),
        ),
    )

def test_rabbitmq_connection():
    params = pika.ConnectionParameters(**get_rabbitmq_params())
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    assert channel.is_open
    connection.close()

def test_queue_declare_and_bind():
    params = pika.ConnectionParameters(**get_rabbitmq_params())
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    queue = "agent_a"
    channel.exchange_declare(exchange='agent_communication', exchange_type='topic', durable=True)
    channel.queue_declare(queue=queue, durable=True)
    channel.queue_bind(exchange='agent_communication', queue=queue, routing_key=queue)
    connection.close()

def test_publish_and_consume():
    params = pika.ConnectionParameters(**get_rabbitmq_params())
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    queue = "agent_a_test"  # Use a test-specific queue
    test_message = "pytest-message"
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(exchange="", routing_key=queue, body=test_message)
    time.sleep(0.1)  # Give RabbitMQ a moment to process
    method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=True)
    assert body is not None, "No message found in the queue"
    assert body.decode() == test_message
    connection.close()