import boto3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_user_topics():
    """Find and delete all SNS topics with the prefix 'wingsight-user-'"""
    try:
        sns = boto3.client('sns')
        
        # List all topics
        paginator = sns.get_paginator('list_topics')
        topic_count = 0
        deleted_count = 0
        
        for page in paginator.paginate():
            for topic in page['Topics']:
                topic_arn = topic['TopicArn']
                topic_name = topic_arn.split(':')[-1]
                
                if topic_name.startswith('wingsight-user-'):
                    topic_count += 1
                    logger.info(f"Found user topic: {topic_name}")
                    
                    try:
                        sns.delete_topic(TopicArn=topic_arn)
                        deleted_count += 1
                        logger.info(f"Deleted topic: {topic_name}")
                    except Exception as e:
                        logger.error(f"Failed to delete topic {topic_name}: {str(e)}")
        
        logger.info(f"Cleanup complete. Found {topic_count} user topics, deleted {deleted_count}.")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    cleanup_user_topics()