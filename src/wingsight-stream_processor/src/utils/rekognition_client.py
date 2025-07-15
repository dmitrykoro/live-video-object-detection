import io
import os
import boto3
import base64
import requests
import numpy as np

from PIL import Image


class RekognitionClient:
    """Client for interacting with AWS Rekognition for bird detection and classification"""
    
    def __init__(self, region_name="us-east-1", min_confidence=80.0):
        """
        Initialize the Rekognition client
        
        Args:
            region_name: AWS region name
            min_confidence: Minimum confidence threshold for detection (0-100)
        """
        # Try to get region from environment if not provided
        if region_name is None:
            region_name = os.environ.get('AWS_REGION', 'us-east-1')
        
        self.region_name = region_name
        self.min_confidence = min_confidence
        
        # Create boto3 client - it will automatically use credentials from:
        # 1. Environment variables
        # 2. ~/.aws/credentials file
        # 3. IAM role if running on EC2/Lambda
        self.rekognition = boto3.client('rekognition', region_name=self.region_name)
        
        # List of general bird taxonomic labels that should be considered less specific
        self.general_bird_categories = [
            'Bird', 'Aves', 'Avian', 'Fowl'
        ]
        
        # List of specific bird species/types that Rekognition can detect
        self.specific_bird_species = [
            'Eagle', 'Hawk', 'Falcon', 'Owl', 'Robin', 'Sparrow', 'Duck', 'Swan', 
            'Goose', 'Hummingbird', 'Penguin', 'Seagull', 'Pelican', 'Woodpecker', 
            'Jay', 'Cardinal', 'Flamingo', 'Pigeon', 'Dove', 'Parrot', 'Macaw', 
            'Peacock', 'Crow', 'Raven', 'Chicken', 'Turkey', 'Ostrich', 'Finch', 
            'Canary', 'Bluebird', 'Kingfisher', 'Bald Eagle', 'Blue Jay', 'Red Robin',
            'Mockingbird', 'Warbler', 'Nightingale', 'Parakeet', 'Cockatoo', 'Toucan',
            'Albatross', 'Heron', 'Egret', 'Stork', 'Ibis', 'Sandpiper', 'Puffin',
            'Quail', 'Pheasant', 'Vulture', 'Condor', 'Hummingbird'
        ]
        
        # Non-bird animals we want to explicitly exclude
        self.non_bird_animals = [
            'Dog', 'Cat', 'Mammal', 'Reptile', 'Fish', 'Amphibian', 'Insect', 
            'Animal', 'Wildlife', 'Bear', 'Lion', 'Tiger', 'Deer', 'Fox', 'Wolf',
            'Squirrel', 'Rabbit', 'Horse', 'Cow', 'Sheep', 'Goat', 'Elephant',
            'Giraffe', 'Monkey', 'Ape', 'Gorilla', 'Chimpanzee', 'Snake', 'Lizard'
        ]
    
    def classify_image(self, image):
        """
        Classify a PIL Image using AWS Rekognition
        
        Args:
            image: PIL.Image object
        
        Returns:
            Dict containing species name and confidence
        """
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        try:
            # Call Rekognition DetectLabels API with higher MaxLabels to catch specific species
            response = self.rekognition.detect_labels(
                Image={'Bytes': img_bytes},
                MaxLabels=50,  # Increased to catch more potential species
                MinConfidence=self.min_confidence
            )
            
            # Check for presence of any bird label first
            has_any_bird = False
            for label in response['Labels']:
                if label['Name'] in self.specific_bird_species or label['Name'] in self.general_bird_categories or 'bird' in label['Name'].lower():
                    has_any_bird = True
                    break
            
            # If no birds at all, return early
            if not has_any_bird:
                return {
                    "bird_detected": False,
                    "top_species": [],
                    "other_objects": self._get_top_non_bird_objects(response['Labels'])
                }
            
            # Process results to find bird-related labels
            specific_bird_labels = []
            general_bird_labels = []
            
            for label in response['Labels']:
                label_name = label['Name']
                
                # Skip any known non-bird animals
                if label_name in self.non_bird_animals:
                    continue
                    
                # Check if this is a specific bird species
                if label_name in self.specific_bird_species:
                    specific_bird_labels.append({
                        'species': label_name,
                        'confidence': label['Confidence'],
                        'is_specific': True
                    })
                # Check if this is a general bird category
                elif label_name in self.general_bird_categories or 'bird' in label_name.lower():
                    general_bird_labels.append({
                        'species': label_name,
                        'confidence': label['Confidence'],
                        'is_specific': False
                    })
            
            # Combine and sort all bird labels, prioritizing specific species
            all_bird_labels = specific_bird_labels + general_bird_labels
            
            # If we found bird labels
            if all_bird_labels:
                # Sort by confidence (highest first)
                all_bird_labels.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Take up to 5 labels
                top_birds = all_bird_labels[:5]
                
                # Check if we have any specific species
                has_specific_species = any(bird['is_specific'] for bird in top_birds)
                
                return {
                    "bird_detected": True,
                    "top_species": top_birds,
                    "has_specific_species": has_specific_species,
                    "primary_species": top_birds[0]['species'],
                    "primary_confidence": top_birds[0]['confidence']
                }
            else:
                # No birds detected at all
                return {
                    "bird_detected": False,
                    "top_species": [],
                    "other_objects": self._get_top_non_bird_objects(response['Labels'])
                }
            
        except Exception as e:
            print(f"Error calling AWS Rekognition: {str(e)}")
            return {"error": str(e)}
    
    def _get_top_non_bird_objects(self, labels, max_objects=5):
        """Extract top non-bird objects from recognition results"""
        non_bird_objects = []
        
        for label in labels:
            label_name = label['Name']
            # Skip bird-related labels and focus on other objects
            if (label_name not in self.specific_bird_species and 
                label_name not in self.general_bird_categories and 
                'bird' not in label_name.lower()):
                non_bird_objects.append({
                    'name': label_name,
                    'confidence': label['Confidence']
                })
                
                # Limit to max_objects
                if len(non_bird_objects) >= max_objects:
                    break
                    
        return non_bird_objects
    
    def classify_image_file(self, image_path):
        """Classify a bird image from a file path"""
        try:
            image = Image.open(image_path)
            return self.classify_image(image)
        except Exception as e:
            print(f"Error processing image file: {str(e)}")
            return {"error": str(e)}
    
    def classify_base64_image(self, base64_string):
        """Classify a bird image from a base64-encoded string"""
        try:
            # Decode the base64 string
            if "base64," in base64_string:
                # Remove data URL prefix if present
                base64_string = base64_string.split("base64,")[1]
            
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            return self.classify_image(image)
        except Exception as e:
            print(f"Error processing base64 image: {str(e)}")
            return {"error": str(e)}
        
    def classify_image_url(self, image_url):
        """Classify a bird image from a URL
        
        Args:
            image_url: URL pointing to an image
            
        Returns:
            Dict containing species name and confidence
        """
        try:
            # Download the image from the URL
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Convert to PIL Image
            image_data = response.content
            image = Image.open(io.BytesIO(image_data))
            
            # Use existing method to classify
            return self.classify_image(image)
            
        except requests.RequestException as e:
            print(f"Error downloading image from URL: {str(e)}")
            return {"error": f"Failed to download image from URL: {str(e)}"}
        except Exception as e:
            print(f"Error processing image from URL: {str(e)}")
            return {"error": str(e)}
    
    def classify_numpy_array(self, numpy_array):
        """
        Classify a bird image from a numpy array (OpenCV format)
        
        Args:
            numpy_array: numpy.ndarray in BGR format (OpenCV default)
            
        Returns:
            Dict containing species name and confidence
        """
        try:
            # Validate input type
            if not isinstance(numpy_array, np.ndarray):
                raise ValueError(f"Expected numpy.ndarray, got {type(numpy_array)}")
            
            # Convert BGR to RGB (OpenCV uses BGR, PIL uses RGB)
            if len(numpy_array.shape) == 3 and numpy_array.shape[2] == 3:  # Ensure 3-channel color image
                rgb_array = numpy_array[:, :, ::-1]  # Reverse color channels
                image = Image.fromarray(rgb_array)
            elif len(numpy_array.shape) == 2:  # Grayscale image
                image = Image.fromarray(numpy_array)
            else:
                raise ValueError("Unsupported numpy array shape for image")
                
            # Use existing method to classify
            return self.classify_image(image)
            
        except Exception as e:
            print(f"Error processing numpy array: {str(e)}")
            return {"error": str(e)}
