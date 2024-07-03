from dotenv import load_dotenv
import os

load_dotenv()  # This will load environment variables from a .env file

DATABASE_URL = os.getenv('DATABASE_URL')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')