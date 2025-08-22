from intugle.common.resources.base import BaseResource
from intugle.models.resources.model import Model
from intugle.models.resources.relationship import Relationship
from intugle.models.resources.source import Source


class Resource:
    model_factory = {
        'models': Model,
        'relationships': Relationship,
        'sources': Source
    }

    def create_resource(self, resouce_type: str, data: dict):
        model_cls = self.model_factory.get(resouce_type.lower())
        if not model_cls:
            raise ValueError(f"Resource model: {resouce_type}")
        return model_cls(**data)
    
    @classmethod
    def get_resource(self, resource_type: str) -> BaseResource:
        return self.model_factory.get(resource_type)
