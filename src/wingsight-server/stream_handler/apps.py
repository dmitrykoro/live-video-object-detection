import os
import threading
import logging

from django.apps import AppConfig



class StreamHandlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stream_handler'

    logging.basicConfig(level=logging.INFO)
