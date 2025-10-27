import logging
import uuid

from pathlib import Path

import yaml

from intugle.core.exceptions import IntugleException

log = logging.getLogger(__name__)

CONFIG_FILE_NAME = "config.yaml"


class Project:
    """
    Manages the project configuration, specifically the project ID.
    """

    def __init__(self, project_base: str):
        self.project_base = Path(project_base)
        self.config_path = self.project_base / CONFIG_FILE_NAME
        self._project_id = None
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Loads the project config or creates it if it doesn't exist."""
        try:
            self.project_base.mkdir(parents=True, exist_ok=True)
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = yaml.safe_load(f)
                    self._project_id = config.get("project_id")
                if not self._project_id:
                    self._generate_and_save_project_id()
            else:
                self._generate_and_save_project_id()
        except (IOError, yaml.YAMLError) as e:
            raise IntugleException(f"Error loading or creating config file at {self.config_path}: {e}") from e

    def _generate_and_save_project_id(self):
        """Generates a new project ID and saves it to the config file."""
        self._project_id = str(uuid.uuid4())
        config = {"project_id": self._project_id}
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(config, f)
            log.info(f"Generated and saved new project ID: {self._project_id}")
        except IOError as e:
            raise IntugleException(f"Error saving config file at {self.config_path}: {e}") from e

    @property
    def project_id(self) -> str:
        """Returns the project ID."""
        if not self._project_id:
            raise IntugleException("Project ID not loaded.")
        return self._project_id
