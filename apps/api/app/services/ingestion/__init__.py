"""Ingestion service package.

Import concrete classes from their modules. Keeping this package initializer
light avoids pulling database models into unit tests that only need pure
helpers such as the cleaner or URL validator.
"""

from app.services.ingestion.queue import ingestion_queue_manager

