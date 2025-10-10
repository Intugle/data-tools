from typing import Type

from .base import Exporter


class ExporterFactory:
    def __init__(self):
        self._exporters = {}

    def register_exporter(self, format_name: str, exporter_class: Type[Exporter]):
        self._exporters[format_name] = exporter_class

    def get_exporter(self, format_name: str, manifest) -> Exporter:
        exporter_class = self._exporters.get(format_name)
        if not exporter_class:
            raise ValueError(f"Unknown export format: {format_name}")
        return exporter_class(manifest)


factory = ExporterFactory()
