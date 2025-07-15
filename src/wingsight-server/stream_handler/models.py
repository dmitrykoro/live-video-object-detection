import uuid
import threading
import time
import logging
import numpy as np
import json

from django.db import models
from django.db.utils import DatabaseError
from django.utils import timezone
from django.conf import settings

from stream_handler.utils import queue_events

from .custom_exceptions import SubscriptionAlreadyExists
import boto3



class User(models.Model):
    """
    Stores user. Creates subscription.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sns_subscribed = models.BooleanField(default=False)
    sns_topic_arn = models.CharField(max_length=255, blank=True, null=True)  # New field

    def create_sns_topic(self):
        """Create a personal SNS topic for this user."""
        try:
            sns = boto3.client("sns", region_name=settings.AWS_REGION)
            
            # Create a topic with the user's ID (sanitized for SNS naming)
            topic_name = f"wingsight-user-{str(self.id).replace('-', '')}"
            
            response = sns.create_topic(Name=topic_name)
            
            # Store the topic ARN
            self.sns_topic_arn = response['TopicArn']
            self.save(update_fields=['sns_topic_arn'])
            
            logging.info(f"Created SNS topic {self.sns_topic_arn} for user {self.id}")
            return self.sns_topic_arn
        except Exception as e:
            logging.error(f"Failed to create SNS topic for user {self.id}: {str(e)}")
            return None

    class Meta:
        db_table = "user"

    def create_subscription(self, url, frame_fetch_frequency, provide_notification):
        """
        Create a new subscription.
        :param url: URL of the video (can be any Facebook, Twitch or YouTube video)
        :param frame_fetch_frequency: how often to get the frame from the video to recognize the objects
        :param provide_notification: whether to enable notifications for this stream
        :return: StreamSubscription object if created, else raises an exception
        """

        stream_subscription = StreamSubscription.objects.create(
            user=self,
            url=url,
            frame_fetch_frequency=frame_fetch_frequency,
            provide_notification=provide_notification 
        )

        queue_events.publish_stream_event(stream_subscription.id)

        return stream_subscription

    def get_all_stream_subscriptions(self):
        """
        Get all user's streams.
        :return: QuerySet of StreamSubscription
        """

        return StreamSubscription.objects.filter(user=self)


class StreamSubscription(models.Model):
    """
    Is created for every new stream URL provided by user.
    """

    url = models.URLField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    provide_notification = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    frame_fetch_frequency = models.IntegerField()
    last_frame_fetched_at = models.DateTimeField(null=True, blank=True)
    target_bird_species = models.TextField(
        null=True, blank=True, help_text="JSON list of target bird species names to detect"
    )
    misc_info = models.TextField(
        null=True, blank=True, help_text="Can be used for messages from stream parsing backend"
    )
    target_timestamp_ms = models.IntegerField(default=1)

    class Meta:
        db_table = "stream_subscription"

    def deactivate(self):
        """
        Deactivate this subscription. Will kill the thread, stop recognizing objects and provoking notifications.
        """

        self.is_active = False
        self.save()

    def reactivate(self):
        """
        Reactivate the subscription.
        """

        self.is_active = True
        self.save()

        queue_events.publish_stream_event(self.id)

    def delete_subscription(self):
        """
        Same as deactivate, but user won't see the subscription and won't be able to re-activate.
        """

        self.is_active = False
        self.is_deleted = True
        self.save()


class RecognitionEntry(models.Model):
    """
    Is created when something was recognized in the image.
    """

    stream_subscription = models.ForeignKey(
        'StreamSubscription', on_delete=models.CASCADE, related_name='recognition_history'
    )
    earth_timestamp = models.DateTimeField(auto_now_add=True)
    stream_timestamp = models.DateTimeField(auto_now_add=True)
    recognized_specie_name = models.CharField(max_length=255)
    recognized_specie_img_url = models.URLField()

    class Meta:
        db_table = "recognition_entry"
