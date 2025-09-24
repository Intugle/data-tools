from enum import Enum


class NodeType(str, Enum):
    MODEL = "model"
    RELATIONSHIP = "relationship"
