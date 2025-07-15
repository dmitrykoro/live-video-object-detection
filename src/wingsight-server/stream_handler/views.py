import json
import logging
import traceback
import boto3

from rest_framework.response import Response
from rest_framework import status, views
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .serializers import StreamSubscriptionSerializer
from .models import User, StreamSubscription, RecognitionEntry
from .serializers import StreamSubscriptionSerializer, RecognitionEntrySerializer
from .custom_exceptions import SubscriptionAlreadyExists, MessageBrokerNotAvailable


logger = logging.getLogger(__name__)



class AddStreamView(views.APIView):
    """
    Add a new stream for user. URL defines a uniqueness of a stream.
    """

    @swagger_auto_schema(
        operation_summary="Add a new stream for a user. User must exist in the system (do /add_user first)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["url", "frame_fetch_frequency", "user_id"],
            properties={
                "url": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_URI,
                    description="Stream URL (any Facebook or Twitch video URL, but preferably with birds)",
                    default="https://www.facebook.com/PixCamsLiveStream/videos/752316776177904"
                ),
                "frame_fetch_frequency": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    format=openapi.FORMAT_INT32,
                    description="Frame fetch frequency in seconds",
                    default=5
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "provide_notification": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="Set to true to enable SNS notification"
                ),
            },
        ),
        responses={
            201: openapi.Response(description="Stream created successfully"),
            400: openapi.Response(description="Invalid request"),
            503: openapi.Response(description="The message broker for new subscriptions is not running")
        },
    )
    def post(self, request, *args, **kwargs):
        url = request.data.get("url")
        frame_fetch_frequency = request.data.get("frame_fetch_frequency")
        user_id = request.data.get("user_id")
        provide_notification = request.data.get("provide_notification", False)

        if not all([url, frame_fetch_frequency, user_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)

        try:
            subscription = user.create_subscription(url, frame_fetch_frequency, provide_notification)
            return Response(
                data={
                    "status": "created",
                    "message": StreamSubscriptionSerializer(subscription).data
                },
                status=status.HTTP_201_CREATED
            )

        except SubscriptionAlreadyExists:
            return Response(
                data={
                    "status": "error",
                    "message": f"Subscription to URL {url} already exists for user {user_id}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except MessageBrokerNotAvailable:
            return Response(
                data={
                    "status": "error",
                    "message": "Queue message broker not available. Try again in a few moments, or start the broker manually."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except Exception as e:
            return Response(
                data={
                    "status": "error",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeactivateStreamSubscriptionView(views.APIView):
    """
    Deactivate stream subscription for a user.
    """

    @swagger_auto_schema(
        operation_summary="Deactivate user's stream. Deactivation means the stream will not be parsed in a separate "
                          "thread anymore, objects will not be recognized, notifications will not be provided.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "stream_subscription_id"],
            properties={
               "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "stream_subscription_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_INT32,
                    description="StreamSubscription ID (int)"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Stream subscription deactivated successfully"),
            400: openapi.Response(description="Invalid request"),
        },
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        stream_subscription_id = request.data.get("stream_subscription_id")

        if not all([user_id, stream_subscription_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        stream_subscription = get_object_or_404(StreamSubscription, user=user, id=stream_subscription_id)

        try:
            stream_subscription.deactivate()

            return Response(
                data={
                    "status": "deactivated"
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                data={
                    "status": "error",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReactivateStreamSubscriptionView(views.APIView):
    """
    Reactivate stream subscription for a user.
    """

    @swagger_auto_schema(
        operation_summary="Reactivate user's stream.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "stream_subscription_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "stream_subscription_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_INT32,
                    description="StreamSubscription ID (int)"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Stream subscription reactivated successfully"),
            400: openapi.Response(description="Invalid request"),
        },
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        stream_subscription_id = request.data.get("stream_subscription_id")

        if not all([user_id, stream_subscription_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        stream_subscription = get_object_or_404(StreamSubscription, user=user, id=stream_subscription_id)

        try:
            stream_subscription.reactivate()

            return Response(
                data={
                    "status": "reactivated"
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                data={
                    "status": "error",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteStreamSubscriptionView(views.APIView):
    """
    Delete stream subscription for a user.
    """

    @swagger_auto_schema(
        operation_summary="Delete user's stream. Deletion means the stream will be deactivated, and won't be "
                          "accessible y the user anymore.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "stream_subscription_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "stream_subscription_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_INT32,
                    description="StreamSubscription ID (int)"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Stream subscription deleted successfully"),
            400: openapi.Response(description="Invalid request"),
        },
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        stream_subscription_id = request.data.get("stream_subscription_id")

        if not all([user_id, stream_subscription_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        stream_subscription = get_object_or_404(StreamSubscription, user=user, id=stream_subscription_id)

        try:
            stream_subscription.delete_subscription()

            return Response(
                data={
                    "status": "deleted"
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                data={
                    "status": "error",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetAllStreamSubscriptionRecognitionEntriesView(views.APIView):
    """
    Get all recognition entries for a StreamSubscription.
    """

    @swagger_auto_schema(
        operation_summary="Get all recognition entries for a user's  StreamSubscription",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "stream_subscription_id"],
            properties={
               "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "stream_subscription_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_INT32,
                    description="StreamSubscription ID (int)"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Recognition entries fetched successfully"),
            400: openapi.Response(description="Invalid request"),
        },
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        stream_subscription_id = request.data.get("stream_subscription_id")

        if not all([user_id, stream_subscription_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        stream_subscription = get_object_or_404(StreamSubscription, user=user, id=stream_subscription_id)
        all_recognition_entries = RecognitionEntry.objects.filter(stream_subscription=stream_subscription)

        return Response(
            data={
                "status": "fetched",
                "message": {
                    "all_recognition_entries": RecognitionEntrySerializer(all_recognition_entries, many=True).data
                }
            }
        )


class GetAllUserStreamSubscriptionsView(views.APIView):
    """
    Get all streams of a user.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve all stream subscriptions for a given user.",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                description="The ID of the user",
                type=openapi.TYPE_STRING,
                required=True,
                default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
            )
        ],
        responses={
            200: openapi.Response(description="List of stream subscriptions"),
            400: openapi.Response(description="Bad request"),
        },
    )
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": f"Missing user_id in the request query params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        requested_user = User.objects.get(id=user_id)
        if not requested_user:
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": f"User {user_id} does not exist"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        all_stream_subscriptions = requested_user.get_all_stream_subscriptions()

        return Response(
            data={
                "status": "fetched",
                "message": {
                    "all_stream_subscriptions": StreamSubscriptionSerializer(all_stream_subscriptions, many=True).data
                }
            }
        )


class AddUserWithIdView(views.APIView):
    """
    Add a new user with external ID.
    """

    @swagger_auto_schema(
        operation_summary="Create a new user with a username, email and externally generated ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "user_id"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="The username of the user"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="User email"),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
            },
        ),
        responses={
            201: openapi.Response(description="User created successfully"),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Internal server error"),
        },
    )
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        email = request.data.get("email")
        user_id = request.data.get("user_id")

        if not all([username, email, user_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user, created = User.objects.get_or_create(
                username=username, email=email, id=user_id
            )

            # Create an SNS topic for the user if they don't have one
            if not user.sns_topic_arn:
                user.create_sns_topic()

            return Response(
                data={
                    "status": "created",
                    "message": {
                        "user_id": user.id,
                        "sns_topic_created": bool(user.sns_topic_arn)
                    }
                },
                status=status.HTTP_201_CREATED
            )

            # TODO: if user exists throw appropriate response

        except Exception as e:
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

logger = logging.getLogger(__name__)


class ManageSNSSubscriptionView(views.APIView):
    """
    Subscribe/unsubscribe a user to SNS notifications,
    and retrieve current subscription status.
    """

    @swagger_auto_schema(
        operation_summary="Get a user's SNS subscription status",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="The ID of the user",
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Current subscription status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=["none", "pending", "confirmed"]
                        )
                    }
                )
            ),
            400: openapi.Response(description="Missing or invalid user_id"),
            404: openapi.Response(description="User not found")
        }
    )
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "Missing user_id"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)

        if not user.sns_topic_arn:
            return Response({"status": "none"}, status=status.HTTP_200_OK)

        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        subs = self._list_subscriptions_by_email(sns, user.email, user.sns_topic_arn)

        if not subs:
            return Response({"status": "none"}, status=status.HTTP_200_OK)

        arn = subs[0].get("SubscriptionArn")
        if arn == "PendingConfirmation":
            return Response({"status": "pending"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "confirmed"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Subscribe or unsubscribe a user to SNS notifications",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                 "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "action": openapi.Schema(type=openapi.TYPE_STRING, enum=["subscribe", "unsubscribe"])
            }
        ),
        responses={
            200: openapi.Response(description="Subscription status updated"),
            400: openapi.Response(description="Invalid request"),
            404: openapi.Response(description="User not found"),
            500: openapi.Response(description="Server error")
        }
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        action  = request.data.get("action", "subscribe")

        if not user_id:
            return Response({"error": "Missing user_id"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)

        if action == "subscribe":
            success, message = self._subscribe_user(user)
        elif action == "unsubscribe":
            success, message = self._unsubscribe_user(user)
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        status_code = status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"status": success and "success" or "error", "message": message}, status=status_code)

    def _subscribe_user(self, user):
        """
        Ensure the user has an SNS topic and an email subscription,
        resending confirmation if still pending.
        """
        try:
            # Create topic if missing
            if not user.sns_topic_arn:
                user.create_sns_topic()
                if not user.sns_topic_arn:
                    return False, "Failed to create SNS topic for user"

            sns = boto3.client("sns", region_name=settings.AWS_REGION)

            # List any existing subscriptions for this email
            existing = self._list_subscriptions_by_email(sns, user.email, user.sns_topic_arn)

            if existing:
                # Resend if still pending
                for sub in existing:
                    if sub.get("SubscriptionArn") == "PendingConfirmation":
                        sns.subscribe(TopicArn=user.sns_topic_arn, Protocol="email", Endpoint=user.email)
                        user.is_sns_subscribed = True
                        user.save(update_fields=["is_sns_subscribed"])
                        logger.info(f"Resent confirmation email to {user.email}")
                        return True, f"Confirmation email re-sent to {user.email}"
                # Already confirmed
                user.is_sns_subscribed = True
                user.save(update_fields=["is_sns_subscribed"])
                return True, f"User {user.email} is already subscribed."

            # No existing subscription → create new one
            sns.subscribe(TopicArn=user.sns_topic_arn, Protocol="email", Endpoint=user.email)
            user.is_sns_subscribed = True
            user.save(update_fields=["is_sns_subscribed"])
            logger.info(f"SNS subscription requested for {user.email}")
            return True, f"Subscription confirmation sent to {user.email}. Please check your email."

        except Exception as e:
            logger.error(f"Failed to subscribe {user.email}: {e}")
            return False, f"Failed to subscribe: {str(e)}"

    def _unsubscribe_user(self, user):
        """
        Unsubscribe the user's email from their SNS topic.
        """
        try:
            if not user.sns_topic_arn:
                return True, f"User {user.email} has no active SNS topic."

            sns = boto3.client("sns", region_name=settings.AWS_REGION)
            subs = sns.list_subscriptions_by_topic(TopicArn=user.sns_topic_arn).get("Subscriptions", [])

            for sub in subs:
                if sub.get("Protocol") == "email" and sub.get("Endpoint") == user.email:
                    sns.unsubscribe(SubscriptionArn=sub.get("SubscriptionArn"))
                    logger.info(f"Unsubscribed {user.email} from SNS")
            user.is_sns_subscribed = False
            user.save(update_fields=["is_sns_subscribed"])
            return True, f"User {user.email} unsubscribed from notifications."

        except Exception as e:
            logger.error(f"Failed to unsubscribe {user.email}: {e}")
            return False, f"Failed to unsubscribe: {str(e)}"

    def _list_subscriptions_by_email(self, sns_client, email, topic_arn):
        """
        Helper to find all subscriptions on a topic matching the given email.
        """
        try:
            subscriptions = []
            paginator = sns_client.get_paginator("list_subscriptions_by_topic")
            for page in paginator.paginate(TopicArn=topic_arn):
                for sub in page.get("Subscriptions", []):
                    if sub.get("Protocol") == "email" and sub.get("Endpoint") == email:
                        subscriptions.append(sub)
                if not page.get("NextToken"):
                    break
            return subscriptions
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            return []
        
class ToggleStreamNotificationView(views.APIView):
    """
    Toggle notification settings for a specific stream subscription.
    """

    @swagger_auto_schema(
        operation_summary="Toggle notifications for a stream subscription",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["subscription_id"],
            properties={
                "subscription_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="StreamSubscription ID"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Notification setting toggled"),
            400: openapi.Response(description="Missing input"),
            404: openapi.Response(description="Subscription not found"),
        },
    )
    def post(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")

        if not subscription_id:
            return Response(
                {"error": "Missing subscription_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscription = get_object_or_404(StreamSubscription, id=subscription_id)
            subscription.provide_notification = not subscription.provide_notification
            subscription.save()
            
            return Response({
                "status": "success",
                "new_value": subscription.provide_notification,
                "message": f"Notifications {'enabled' if subscription.provide_notification else 'disabled'} for this stream."
            })
                
        except StreamSubscription.DoesNotExist:
            return Response(
                {"error": "StreamSubscription not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )



class UpdateStreamSubscriptionTargetSpeciesView(views.APIView):
    """
    Update the target bird species for a stream subscription.
    """

    @swagger_auto_schema(
        operation_summary="Update target bird species for stream subscription. Only these species will trigger notifications.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "stream_subscription_id", "target_species"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The ID of the user",
                    default="29e27fff-b9b0-4b90-aac7-48cadb8b2387"
                ),
                "stream_subscription_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    format=openapi.FORMAT_INT32,
                    description="StreamSubscription ID (int)"
                ),
                "target_species": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="List of bird species names to detect (case-sensitive, e.g., ['Eagle', 'Blue Jay', 'Cardinal'])"
                ),
            },
        ),
        responses={
            200: openapi.Response(description="Target species updated successfully"),
            400: openapi.Response(description="Invalid request"),
            404: openapi.Response(description="User or subscription not found"),
            500: openapi.Response(description="Internal server error"),
        },
    )
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        stream_subscription_id = request.data.get("stream_subscription_id")
        target_species = request.data.get("target_species", [])

        logging.info(f"Received update request: user_id={user_id}, subscription_id={stream_subscription_id}, target_species={target_species}")

        if not all([user_id, stream_subscription_id]):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "Missing required body params"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the target_species is a list
        if target_species and not isinstance(target_species, list):
            return Response(
                data={
                    "status": "error",
                    "message": {
                        "error_description": "target_species must be a list"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert stream_subscription_id to integer if it's a string
        if isinstance(stream_subscription_id, str) and stream_subscription_id.isdigit():
            stream_subscription_id = int(stream_subscription_id)
            logging.info(f"Converted subscription_id to int: {stream_subscription_id}")

        try:
            # Get the user first
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    data={"status": "error", "message": f"User with id {user_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Then get the subscription for this user
            try:
                stream_subscription = StreamSubscription.objects.get(user=user, id=stream_subscription_id)
                logging.info(f"Found subscription: {stream_subscription.id}, current target species: {stream_subscription.target_bird_species}")
            except StreamSubscription.DoesNotExist:
                return Response(
                    data={"status": "error", "message": f"Stream subscription {stream_subscription_id} not found for user {user_id}"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize target_species to JSON
            json_species = json.dumps(target_species)
            logging.info(f"JSON serialized species: {json_species}")
            
            # Use transaction to ensure atomicity
            with transaction.atomic():
                # Update the field
                stream_subscription.target_bird_species = json_species
                stream_subscription.save(update_fields=["target_bird_species"])
                logging.info(f"Saved subscription with new target species")
            
            # Verify the update by getting a fresh instance
            fresh_subscription = StreamSubscription.objects.get(id=stream_subscription_id)
            stored_species = json.loads(fresh_subscription.target_bird_species) if fresh_subscription.target_bird_species else []
            logging.info(f"Verified stored species: {stored_species}")
            
            # Check if update was successful
            update_successful = set(stored_species) == set(target_species)
            if not update_successful:
                logging.warning(f"UPDATE VERIFICATION FAILED! Expected: {target_species}, Got: {stored_species}")

            return Response(
                data={
                    "status": "updated" if update_successful else "partial_update",
                    "message": {
                        "subscription_id": stream_subscription.id,
                        "target_species": target_species,
                        "stored_species": stored_species,
                        "update_verified": update_successful
                    }
                },
                status=status.HTTP_200_OK
            )

        except json.JSONDecodeError as e:
            logging.error(f"JSON error: {str(e)}")
            return Response(
                data={"status": "error", "message": f"JSON error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logging.error(f"Error updating target species: {str(e)}")
            logging.error(traceback.format_exc())
            return Response(
                data={"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
