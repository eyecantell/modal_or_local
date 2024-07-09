import logging
import os
from logging.config import dictConfig

# Define the base directory for your application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the logs directory relative to the base directory
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Create the logs directory if it doesn't exist
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s:%(levelname)s - %(message)s - %(pathname)s:%(lineno)s-',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'level': 'INFO',
            'filename': os.path.join(LOGS_DIR, 'app.log'),
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'modal_or_local': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("modal_or_local." + __name__)