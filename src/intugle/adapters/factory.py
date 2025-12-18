import importlib

from typing import Any, Callable, Type, Union

from .adapter import Adapter


class ModuleInterface:
    """Represents a plugin interface. A plugin has a single register function."""

    @staticmethod
    def register() -> None:
        """Register the necessary items in the environment factory."""


def import_module(name: str) -> ModuleInterface:
    """Imports a module given a name."""
    return importlib.import_module(name)  # type: ignore


# --- the new helper function ---
def is_safe_plugin_name(plugin_name: str) -> bool:
    """
    Checks if the plugin belongs to the safe 'intugle.adapters.types' namespace.
    """
    return plugin_name.startswith("intugle.adapters.types.")


DEFAULT_PLUGINS = [
    "intugle.adapters.types.pandas.pandas",
    "intugle.adapters.types.duckdb.duckdb",
    "intugle.adapters.types.snowflake.snowflake",
    "intugle.adapters.types.databricks.databricks",
    "intugle.adapters.types.postgres.postgres",
    "intugle.adapters.types.mysql.mysql",
    "intugle.adapters.types.mariadb.mariadb",
    "intugle.adapters.types.sqlserver.sqlserver",
    "intugle.adapters.types.sqlite.sqlite",
    "intugle.adapters.types.bigquery.bigquery",
    "intugle.adapters.types.oracle.oracle",
]


class AdapterFactory:
    dataframe_funcs: dict[str, tuple[Callable[[Any], bool], Callable[..., Adapter]]] = {}
    config_types: list[Type[Any]] = []

    # LOADER
    def __init__(self, plugins: list[dict] = None):
        if plugins is None:
            plugins = []

        plugins.extend(DEFAULT_PLUGINS)

        for _plugin in plugins:
            # Security check: Ensure the plugin is in the correct namespace
            if not is_safe_plugin_name(_plugin):
                print(f"Warning: Skipping potentially unsafe plugin '{_plugin}'.")
                continue
            try:
                plugin = import_module(_plugin)
                plugin.register(self)
            except ImportError:
                print(f"Warning: Could not load plugin '{_plugin}' due to missing dependencies. This adapter will not be available.")
                pass

    @classmethod
    def register(
        cls,
        env_type: str,
        checker_fn: Callable[[Any], bool],
        creator_fn: Callable[..., Adapter],
        config_type: Type[Any],
    ) -> None:
        """Register a new execution engine type with its configuration type"""
        cls.dataframe_funcs[env_type] = (checker_fn, creator_fn)
        if config_type is not None and config_type not in cls.config_types:
            cls.config_types.append(config_type)

    @classmethod
    def unregister(cls, env_type: str) -> None:
        """Unregister a new execution engine type"""
        cls.dataframe_funcs.pop(env_type, None)

    @classmethod
    def get_dataset_data_type(cls) -> Type[Any]:
        """Dynamically constructs the DataSetData Union type from registered config types"""
        if not cls.config_types:
            return Any
        if len(cls.config_types) == 1:
            return cls.config_types[0]
        return Union[tuple(cls.config_types)]  # noqa: UP007

    @classmethod
    def create(cls, df: Any) -> Adapter:
        """Create a execution engine type"""
        for checker_fn, creator_fn in cls.dataframe_funcs.values():
            if checker_fn(df):
                return creator_fn()
        raise ValueError(f"No suitable dataframe type found for object of type {type(df)!r}")
