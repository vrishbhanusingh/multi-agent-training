import pika
import json
from typing import Callable, Any, Optional

class RabbitMQClient:
    def __init__(self, host: str = "rabbitmq", port: int = 5672, 
                 username: str = "admin", password: str = "admin"):
        self.credentials = pika.PlainCredentials(username, password)
        self.connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=self.credentials
        )
        self.connection = None
        self.channel = None

    async def connect(self):
        """Establish connection to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()
            
            # Declare exchanges
            self.channel.exchange_declare(
                exchange='agent_communication',
                exchange_type='topic'
            )
            
            # Declare default queues
            self.channel.queue_declare(queue='agent_tasks')
            self.channel.queue_declare(queue='agent_responses')

    async def send_message(self, routing_key: str, message: Any) -> bool:
        """Send message to a specific routing key"""
        try:
            await self.connect()
            self.channel.basic_publish(
                exchange='agent_communication',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    async def create_agent_queue(self, agent_id: str) -> bool:
        """Create a dedicated queue for an agent"""
        try:
            await self.connect()
            queue_name = f"agent_{agent_id}"
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            # Bind queue to exchange with agent-specific routing key
            self.channel.queue_bind(
                exchange='agent_communication',
                queue=queue_name,
                routing_key=f"agent.{agent_id}.*"
            )
            return True
        except Exception as e:
            print(f"Error creating agent queue: {e}")
            return False

    def start_consuming(self, queue_name: str, callback: Callable):
        """Start consuming messages from a queue"""
        try:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
            print(f" [*] Waiting for messages in {queue_name}. To exit press CTRL+C")
            self.channel.start_consuming()
        except Exception as e:
            print(f"Error starting consumer: {e}")

    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close() 