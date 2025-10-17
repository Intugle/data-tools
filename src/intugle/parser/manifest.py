import os

from typing import Optional

import yaml

from pydantic import ValidationError

from intugle.common.exception import errors
from intugle.common.resources.base import BaseResource
from intugle.models.manifest import Manifest
from intugle.models.resources import Resource
from intugle.models.resources.source import Source, SourceTables


class FileReaderFromFileSystem:
    """Reads files from the file system and provides methods to filter and read YAML files."""

    def __init__(self, models_dir_path: str):
        """Initializes the file reader with the models directory path.

        Args:
            models_dir_path (str): The base directory path of the models.

        Attributes:
            models_dir_path (str): Stores the base directory path of the models.
            _files (Optional[str]): A list to store file paths, initialized as None.
        """
        self.models_dir_path = models_dir_path
        self._files: Optional[str] = None

    def get_files(self):
        """Retrieves all files from the models directory path.

        This method walks through the directory structure starting from the models directory path
        and collects all file paths into the _files attribute.
        """
        _files = []

        # Walk through the directory structure and collect file paths
        for root, _, fs in os.walk(self.models_dir_path):
            for file in fs:
                _files.append(os.path.join(root, file))

        self._files = _files

    @property
    def files(self):
        """Returns the list of files in the models directory path."""
        if self._files is None:
            self.get_files()
        return self._files

    def read_yaml(self, file_path: str):
        """Reads a YAML file and returns its contents as a dictionary."""
        try:
            with open(file_path, "r") as stream:
                data: dict = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise errors.ParseError(file=file_path, msg=str(exc))
        return data

    def filter_yaml_files(self):
        """Filters the list of files to include only YAML files."""
        return [f for f in self.files if f.endswith((".yaml", ".yml"))]


class ManifestLoader:
    """
    Loads and parses manifest files for a data project.

    This class is responsible for reading YAML manifest files from a given models directory path,
    parsing their contents, and populating a Manifest object with sources and other resources.
    """

    def __init__(self, models_dir_path: str):
        """
        Initializes the parser with the given models directory path.

        Args:
            models_dir_path (str): The base directory path of the models.

        Attributes:
            models_dir_path (str): Stores the base directory path of the models.
            manifest (Manifest): An instance of the Manifest class for managing project manifests.
        """
        self.models_dir_path = models_dir_path
        self.manifest = Manifest()

    def parse_source(self, srcs: dict):
        """Parses source definitions from the manifest data.

        Args:
            srcs (dict): A dictionary containing source definitions, where each key is a source name
                         and the value is a list of tables associated with that source.
        """

        # Iterate through each source definition
        # and create Source and SourceTables objects
        for src in srcs:
            # Pop the tables key from source as in yaml it contains list of tables 
            # but we require a single source to contain single table
            tables = src.pop("tables", None)
            if tables is None:
                tables = [src.pop("table")]

            # iterate through each table and get sources
            for table in tables:
                # create new source object for each table
                source = Source.model_validate(src)

                source_table = SourceTables.model_validate(table)
                source.table = source_table

                self.manifest.sources[source.table.name] = source

    def parse_resource(self, data: dict, resource: str, resource_model: BaseResource):
        """Parses a specific resource type from the manifest data.

        Args:
            data (dict): A dictionary containing resource definitions.
            resource (str): The type of resource being parsed (e.g., 'sources', 'models', 'relationships').
            resource_model (BaseResource): The model class for the resource type.

        Raises:
            ValueError: If the resource type is not recognized.
        """
        # get the resource from manifest SOURCES, MODELS, RELATIONSHIPS
        resource_data = getattr(self.manifest, resource)

        # iterate through each resource data and validate it and add it to the manifest
        for d in data:
            d1 = resource_model.model_validate(d)

            resource_data[d1.name] = d1

    # FIXME better parser is very bad
    def parse_file_resources(self, data: dict):
        """Parses resources from a manifest file.
        
        Args:
            data (dict): A dictionary read from a YAML file, containing resource definitions.
        """
        # iterate through each resources of the data
        for resource, value in data.items():
            # get the resource model from the Resource class depending on the resource type
            resource_model = Resource.get_resource(resource)
            if resource_model is None:
                continue

            # parse the resource based on its type
            if resource == "sources":
                self.parse_source(value)
            else:
                self.parse_resource(value, resource, resource_model)

    def load(self):
        """Loads and parses all manifest files in the models directory path."""

        # get the file reader instance
        file_reader = FileReaderFromFileSystem(self.models_dir_path)

        # get all yamls from the models directory path
        yaml_files = file_reader.filter_yaml_files()

        # iterate through each yaml file and read its contents and populate the manifest
        for yaml_file in yaml_files:
            data = file_reader.read_yaml(yaml_file)

            if data is None:
                continue

            try:
                self.parse_file_resources(data)
            except ValidationError as exc:
                err = exc.errors(include_url=False)
                raise errors.ParseError(file=yaml_file, msg=str(err))
