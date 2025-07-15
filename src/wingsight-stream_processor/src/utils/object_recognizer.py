import logging
import boto3
import json
import requests
import numpy as np

from .s3_thumbnail_uploader import put_to_bucket

from datetime import datetime, UTC

from utils.rekognition_client import RekognitionClient
from models import StreamSubscription, RecognitionEntry, User

from config import AWS_REGION, API_URL


class ObjectRecognizer:
    """
    Class is assigned to every video parsing stream.
    """

    def __init__(
            self,
            db_session,
            stream_subscription_id
    ):
        self.db_session = db_session
        self.stream_subscription_id = stream_subscription_id
        self.rekognition_client = RekognitionClient()

    def handle_image_objects(self, image=None, target_species=None):
        """
        Analyze the image for birds using Rekognition and create recognition entries
        for any birds detected.
        
        1. Analyze the image for birds using Rekognition;
        2. Create recognition entries in the DB for any birds detected;
        3. Notify user through SNS if matches with desired species.
        
        Args:
            image: The image data as numpy array (uses last_fetched_frame if None)
            target_species: Optional list of specific bird species to detect (uses stored targets if None)
        
        Returns:
            (success, message) tuple
        """
        try:
            # Use provided image or last fetched frame
            img = image if image is not None else self.last_fetched_frame
            
            # Validate image format
            if not isinstance(img, np.ndarray):
                logging.error(f"Invalid image type: {type(img)}, expected numpy array")
                return False, "Invalid image format"

            # Get target species (from parameter, database, or empty list)
            species_targets = self._get_target_species(target_species)
            
            # Process image with Rekognition
            result = self.rekognition_client.classify_numpy_array(img)
            
            # Exit early if no birds detected
            if not result.get("bird_detected", False) or not result.get("primary_species"):
                return False, "No birds detected"
                
            # Extract bird detection details
            primary_species = result.get('primary_species')
            primary_confidence = result.get('primary_confidence', 0)
            is_specific_bird = primary_species in self.rekognition_client.specific_bird_species
            
            # Simple anti-spam filter: Check if the most recent detection is the same species
            last_entry = (
            self.db_session.query(RecognitionEntry)
            .filter_by(stream_subscription_id=self.stream_subscription_id)
            .order_by(RecognitionEntry.earth_timestamp.desc())
            .first()
        )
            
            # If the last detection was the same species, skip
            if last_entry and last_entry.recognized_specie_name == primary_species:
                logging.info(f"[StreamSubscription {self.stream_subscription_id}] Skipping duplicate detection for {primary_species}")
                return False, f"Duplicate detection of {primary_species} skipped"
            
            # Check if this species matches user's targets (if any specified)
            has_targets = species_targets and len(species_targets) > 0
            matches_target = not has_targets or primary_species in species_targets
            
            # Only proceed if no targets specified or bird matches targets
            if not matches_target:
                logging.debug(f"Bird {primary_species} detected but not in target list: {species_targets}")
                return False, f"Bird detected but not in target list: {primary_species}"
                
            # Log detection
            logging.info(f"Bird detected: {primary_species} with confidence {primary_confidence:.2f}%")
            
            # Save detection to database with S3 image
            try:
                s3_img_url = put_to_bucket(image, self.stream_subscription_id)

                entry = RecognitionEntry(
                        stream_subscription_id=self.stream_subscription_id,
                        earth_timestamp=datetime.now(UTC),
                        stream_timestamp=datetime.now(UTC),
                        recognized_specie_name=result.get('primary_species'),
                        recognized_specie_img_url=s3_img_url
                )
                self.db_session.add(entry)
                self.db_session.commit()
            
            except Exception as e:
                logging.error(f"Error saving bird detection: {str(e)}")
                return False, f"Error saving detection: {str(e)}"
            
            try:
                stream_subscription = self.db_session.get(StreamSubscription, self.stream_subscription_id)
            except Exception as e:
                logging_prefix = f"[StreamSubscription {self.stream_subscription_id}] "
                logging.error(logging_prefix + f"Error while accessing database: {e}")
                return False, f"Error accessing database: {str(e)}"
            
            # Send notification if confidence is high enough
            should_notify = (primary_confidence > 90 or is_specific_bird) and stream_subscription.provide_notification
            if should_notify:
                return self.notify_user(primary_species, primary_confidence)
                
            return True, f"Bird {primary_species} detected and recorded"
            
        except Exception as e:
            logging.error(f"Error in bird recognition: {str(e)}")
            return False, f"Error in recognition: {str(e)}"
        
    def _get_target_species(self, target_species=None):
        """Helper method to get target species from parameter or database"""
        if target_species is not None:
            return target_species
            
        try:
            # Refresh subscription data from database
            fresh_subscription = self.db_session.get(StreamSubscription, self.stream_subscription_id)
            if fresh_subscription.target_bird_species:
                return json.loads(fresh_subscription.target_bird_species)
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Error loading target species: {str(e)}")
        
        return []  # Default to empty list if no targets found
            

    def notify_user(self, species, confidence):
        logging_prefix = f"[StreamSubscription {self.stream_subscription_id}] "

        try:
            stream_subscription = self.db_session.get(StreamSubscription, self.stream_subscription_id)
        except Exception as e:
            logging.error(logging_prefix + f"Error while accessing database: {e}")
            return False, f"Error accessing database: {str(e)}"
        
        if not stream_subscription.provide_notification:
            return False, "Notifications are disabled for this subscription"
        
        apiUrl = API_URL   # Create a new audio file if it does not exist already.
        logging.info(f"Polly API: {apiUrl}")
        headers = {
            "Content-Type": "application/json"
        }
        payload = { 
            "text" : str(species)
        }
        # FRONTEND will use lambda GET to get the bird type from DB
        try:
            response = requests.post(apiUrl, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                logging.info(f"{response.text}")
            else:
                logging.error(f"Failed to send bird type to Lambda: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error while calling Lambda function: {str(e)}")

        try:
            sns = boto3.client("sns", region_name=AWS_REGION)
            
            try:
                user = self.db_session.get(User, stream_subscription.user_id)
            except Exception as e:
                logging.error(f"Error accessing user: {e}")
                return False, f"Error accessing user: {str(e)}"
            
            if not user.sns_topic_arn:
                logging.warning(f"User {user.id} doesn't have an SNS topic ARN")
                return False, "User doesn't have an SNS topic configured"
                
            # Get count of user's streams for better notification
            user_stream_count = (
                self.db_session.query(StreamSubscription)
                .filter_by(user_id=user.id)
                .count()
            )

            logging.info(logging_prefix + f'user stream count : {user_stream_count}')
            
            # Get position of this stream in user's streams
            user_stream_position = 1  # Default to 1 if we can't determine position
            if user_stream_count > 1:
                try:
                    # Find this stream's position for the user
                    user_streams = (
                        self.db_session.query(StreamSubscription)
                        .filter_by(user_id=user.id)
                        .order_by(StreamSubscription.created_at)
                        .all()
                    )
                    for i, sub in enumerate(user_streams, 1):
                        if sub.id == self.stream_subscription_id:
                            user_stream_position = i
                            break
                except Exception as e:
                    logging.error(f"Error determining stream position: {e}")
            
            # Create a more informative subject line
            if user_stream_count == 1:
                subject = f"WingSight: {species} Detected in Your Stream!"
            else:
                subject = f"WingSight: {species} Detected in Your Stream #{user_stream_position}!"
                
            message = f"""
                        🦜 Bird Detection Alert! 🦜
                        
                        A {species} was detected in your stream! (Confidence: {confidence:.2f}%)
                        Stream: {stream_subscription.url}
                        Detected at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}
                        
                        Log in to WingSight to view more details.
                        """

            response = sns.publish(
                TopicArn=user.sns_topic_arn,
                Message=message,
                Subject=subject
            )
            return True, f"Notification about {species} sent to {user.email}"
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
            return False, f"Failed to send notification: {str(e)}"
            

