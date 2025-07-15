import pika
import json
import dotenv
import os
import logging

from stream_handler.custom_exceptions import MessageBrokerNotAvailable


dotenv.load_dotenv()

MQ_HOST = os.getenv("MQ_HOST")
QUEUE_NAME = os.getenv("QUEUE_NAME")

MQ_USER = os.getenv("MQ_USER")
MQ_PASSWORD = os.getenv("MQ_PASSWORD")

credentials = pika.PlainCredentials(MQ_USER, MQ_PASSWORD)


def publish_stream_event(subscription_id):
    """
    Create a new queue entry for StreamSubscription.

    :param subscription_id: ID of the subscription. Will be used by stream parser to fetch and update DB.
    """

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(MQ_HOST, credentials=credentials))

    except Exception:
        raise MessageBrokerNotAvailable

    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    message = json.dumps({"subscription_id": str(subscription_id)})

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(delivery_mode=2),
    )

    logging.info(f"Django sent new subscription with id: {subscription_id} to RabbitMQ host: {MQ_HOST}")

    connection.close()
