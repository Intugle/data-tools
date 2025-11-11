import os

from pathlib import Path

from intugle.core import settings


def touch(path: str | Path) -> None:
    """
    Updates the modified time of a file, creating it if it doesn't exist.
    Similar to the 'touch' command in Unix.
    """
    with open(path, 'a'):
        os.utime(path, None)


def update_relationship_file_mtime() -> None:
    """
    Updates the modified time of the relationships file.
    """
    if not settings.RELATIONSHIPS_FILE:
        return

    file_path = os.path.join(settings.MODELS_DIR, settings.RELATIONSHIPS_FILE)
    
    # Check if the file exists before touching it
    if os.path.exists(file_path):
        touch(file_path)
