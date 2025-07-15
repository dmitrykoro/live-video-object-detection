import os

from dotenv import load_dotenv
load_dotenv()


DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")

MQ_USER = os.getenv("MQ_USER")
MQ_PASSWORD = os.getenv("MQ_PASSWORD")

DEPLOYMENT_ENV = os.getenv('DEPLOYMENT_ENV')

if DEPLOYMENT_ENV == "aws":
    DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"

elif DEPLOYMENT_ENV == "local":
    DATABASE_URL = "sqlite:///../wingsight-server/db.sqlite3"


MQ_HOST = os.getenv("MQ_HOST")
MAX_STREAMS_PER_INSTANCE = os.getenv("MAX_STREAMS_PER_INSTANCE")

LOG_LEVEL = os.getenv("LOG_LEVEL")

AWS_REGION = os.getenv("AWS_REGION")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
API_URL = os.getenv("API_URL") # API Gateway URL 4 audio lambda
