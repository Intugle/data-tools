import importlib

from typing import Any, Callable

from .adapter import Adapter


class ModuleInterface:
    """Represents a plugin interface. A plugin has a single register function."""

    @staticmethod
    def register() -> None:
        """Register the necessary items in the environment factory."""


def import_module(name: str) -> ModuleInterface:
    """Imports a module given a name."""
    return importlib.import_module(name)  # type: ignore


DEFAULT_PLUGINS = [
    "intugle.adapters.types.pandas.pandas",
    "intugle.adapters.types.duckdb.duckdb",
]


class AdapterFactory:
    dataframe_funcs: dict[str, tuple[Callable[[Any], bool], Callable[..., Adapter]]] = {}

    # LOADER
    def __init__(self, plugins: list[dict] = None):
        if plugins is None:
            plugins = []

        plugins.extend(DEFAULT_PLUGINS)

        for _plugin in plugins:
            plugin = import_module(_plugin)
            plugin.register(self)

    @classmethod
    def register(
        cls,
        env_type: str,
        checker_fn: Callable[[Any], bool],
        creator_fn: Callable[..., Adapter],
    ) -> None:
        """Register a new execution engine type"""
        cls.dataframe_funcs[env_type] = (checker_fn, creator_fn)

    @classmethod
    def unregister(cls, env_type: str) -> None:
        """Unregister a new execution engine type"""
        cls.dataframe_funcs.pop(env_type, None)

    @classmethod
    def create(cls, df: Any) -> Adapter:
        """Create a execution engine type"""
        for checker_fn, creator_fn in cls.dataframe_funcs.values():
            if checker_fn(df):
                return creator_fn()
        raise ValueError(f"No suitable dataframe type found for object of type {type(df)!r}")
