from enum import Enum


class SmartQueryExceptionType(Enum):
    FIELD = 1


class SmartQueryException(Exception):
    def __init__(
        self, type: SmartQueryExceptionType, message: str, details: dict = {}
    ) -> None:
        self.type = type
        self.message = message
        self.details = details

    def __str__(self):
        return self.message

    def __call__(self):
        return {
            "type": self.type.name,
            "message": self.message,
            "details": self.details,
        }
