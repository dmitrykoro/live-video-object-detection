import pika
import json
import logging
import subprocess
import cv2
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC
from concurrent.futures import ThreadPoolExecutor

from models import StreamSubscription
from config import DATABASE_URL, MQ_HOST, MQ_USER, MQ_PASSWORD, MAX_STREAMS_PER_INSTANCE
from utils.object_recognizer import ObjectRecognizer


QUEUE_NAME = "new_stream_subscriptions"

executor = ThreadPoolExecutor(max_workers=int(MAX_STREAMS_PER_INSTANCE))

logging.basicConfig(level=logging.DEBUG)


engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def get_live_stream_url(subscription_url):
    """
    Get live stream url from standard video url.
    """

    try:
        result = subprocess.run(
            [
                "yt-dlp", "-g", "-f", "b", "--no-playlist",
                subscription_url
            ],
            capture_output=True, text=True, check=True
        )
        stream_url = result.stdout.strip()
        logging.info(f"[yt-dlp] Retrieved stream URL for {subscription_url}. Retrieved URL: {stream_url}")

        return stream_url

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to retrieve stream URL for {subscription_url}. "
            f"yt-dlp error: {e.stderr}. "
            f"Retrying..."
        )

def obtain_video_capture(video_url):
    """
    Get OpenCV VideoCapture
    :param video_url: client-provided url of the video
    :return: cv2.VideoCapture
    """

    stream_url = get_live_stream_url(video_url)
    logging.debug(f"Obtained live stream URL: {stream_url}")

    return cv2.VideoCapture(stream_url)


def parse_thread(subscription_id):
    """
    Parse video thread while it is active.
    """

    logging_prefix = f"[StreamSubscription {subscription_id}] "

    session = Session()
    logging.info(logging_prefix + f"Starting stream parser...")

    try:
        stream_subscription = session.get(StreamSubscription, subscription_id)

    except Exception as e:
        logging.error(logging_prefix + f"Error while accessing database: {e}")
        return

    object_recognizer = ObjectRecognizer(
        db_session=session,
        stream_subscription_id=stream_subscription.id
    )

    video_capture = None

    try:
        video_capture = obtain_video_capture(stream_subscription.url)

    except RuntimeError as e:
        logging.error(e)

        stream_subscription.misc_info = f"Unable to parse the stream. Error: {e}"
        session.commit()

    while True and video_capture is not None:
        stream_subscription = session.get(StreamSubscription, subscription_id)

        video_capture = obtain_video_capture(stream_subscription.url) # to update url for platforms that have expired param

        logging.debug(logging_prefix + "Retrieved subscription from DB in a loop...")

        if not stream_subscription:
            logging.error(logging_prefix + "Subscription object not found in the database.")
            break

        time.sleep(stream_subscription.frame_fetch_frequency)

        if not stream_subscription.is_active:
            logging.info(logging_prefix + "Subscription is deactivated, releasing...")
            break

        if not video_capture.isOpened():
            continue

        video_capture.set(cv2.CAP_PROP_POS_MSEC, stream_subscription.target_timestamp_ms)

        stream_subscription.target_timestamp_ms += stream_subscription.frame_fetch_frequency * 1000

        # frame is 3-dimensional ndarray; for 1080x1920 video frame, the ndarray is (1080, 1920, 3)
        frame_read_correctly, frame = video_capture.read()
        if not frame_read_correctly:
            continue

        stream_subscription.last_frame_fetched_at = datetime.now(UTC)
        session.commit()
        logging.info(logging_prefix + "Fetched frame.")

        object_recognizer.handle_image_objects(frame, stream_subscription.target_bird_species)

    video_capture.release()
    session.close()

    return

def handle_message_callback(ch, method, properties, body):
    """
    Handle a new message from RabbitMQ.
    """

    message = json.loads(body)
    subscription_id = message.get("subscription_id")

    executor.submit(parse_thread, subscription_id)
    ch.basic_ack(delivery_tag=method.delivery_tag)


credentials = pika.PlainCredentials(MQ_USER, MQ_PASSWORD)
connection = pika.BlockingConnection(pika.ConnectionParameters(MQ_HOST, credentials=credentials))
channel = connection.channel()
channel.basic_qos(prefetch_count=int(MAX_STREAMS_PER_INSTANCE))
channel.queue_declare(queue=QUEUE_NAME, durable=True)
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_message_callback)

logging.info("[*] Waiting for messages...")
channel.start_consuming()