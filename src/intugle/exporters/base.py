from abc import ABC, abstractmethod

from intugle.models.manifest import Manifest


class Exporter(ABC):
    def __init__(self, manifest: Manifest):
        self.manifest = manifest

    @abstractmethod
    def export(self, **kwargs) -> dict:
        raise NotImplementedError
