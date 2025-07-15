import os
import boto3
import cv2

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client('s3')

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


def put_to_bucket(image, stream_subscription_id):
    """
    Create thumbnail and put into bucket.
    """

    small_image = cv2.resize(image, (320, 240))
    _, buffer = cv2.imencode('.jpg', small_image)
    image_data = buffer.tobytes()

    # Generate a unique S3 object key (e.g., using timestamp or unique ID)
    image_key = f"thumbnails/{stream_subscription_id}/{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=image_key,
        Body=image_data,
        ContentType='image/jpeg'
    )

    return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{image_key}"
