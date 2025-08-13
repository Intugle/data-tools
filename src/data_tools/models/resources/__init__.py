from data_tools.common.resources.base import BaseResource
from data_tools.models.resources.model import Model
from data_tools.models.resources.relationship import Relationship
from data_tools.models.resources.source import Source


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
