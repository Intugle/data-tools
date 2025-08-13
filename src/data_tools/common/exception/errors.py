#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any


class BaseExceptionMixin(Exception):
    """Basic exception mixin class"""

    code: int

    def __init__(self, msg: str = None, *, data: Any = None):
        self.msg = msg
        self.data = data


class CustomError(BaseExceptionMixin):
    """Custom Exception"""

    def __init__(self, msg: str, *, code: int, data: Any = None):
        self.code = code
        super().__init__(msg=msg, data=data)


class UnprocessableEntityError(BaseExceptionMixin):
    """Unprocessable Entity"""

    code = 422

    def __init__(self, msg: str = "Unprocessable Entity", *, data: Any = None):
        super().__init__(msg=msg, data=data)


class NotFoundError(BaseExceptionMixin):
    """Not Found"""

    code = 404

    def __init__(self, msg: str = "Not found", *, data: Any = None):
        super().__init__(msg=msg, data=data)


class RuntimeError(BaseExceptionMixin):
    """Runtime Error"""
    
    code = 500

    def __init__(self, msg: str = "Runtime error", *, file: str = None, data: str = None):
        super().__init__(msg=msg, data=data)
        self.file = file


class ParseError(RuntimeError):
    """Parse Error"""

    code = 400
