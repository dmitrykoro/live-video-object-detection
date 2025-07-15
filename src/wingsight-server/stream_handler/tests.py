from django.test import TestCase

# Create your tests here.

from rekognition_client import RekognitionBirdClassifier
import sys

def test_bird_classifier(image_path):
    """Test the AWS Rekognition-based bird classifier with a local image"""
    print(f"Testing with image: {image_path}")

    # Initialize the classifier
    classifier = RekognitionBirdClassifier()

    # Classify the image
    result = classifier.classify_image_file(image_path)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Classification result:")
        print(f"Species: {result.get('species')}")
        print(f"Confidence: {result.get('confidence'):.2f}%")

    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default to test_bird.jpg if available
        image_path = "test_bird.jpg"

    test_bird_classifier(image_path)
