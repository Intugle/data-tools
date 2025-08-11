#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from data_tools.core.utilities.configs import load_model_configuration


class Settings(BaseSettings):
    """Global Configuration"""

    UPSTREAM_SAMPLE_LIMIT: int = 10000
    MODEL_DIR_PATH: str = str(Path(os.path.split(os.path.abspath(__file__))[0]).parent.joinpath(
        "artifacts"
    ))
    MODEL_RESULTS_PATH: str = os.path.join("model", "model_results")
    
    DI_CONFIG: dict = load_model_configuration('DI', {})
    KI_CONFIG: dict = load_model_configuration('KI', {})

    DI_MODEL_VERSION: str = "13052023"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )
    L2_SAMPLE_LIMIT: int = 10

    # LLM CONFIGS
    LLM_TYPE: str = "azure"


@lru_cache
def get_settings() -> Settings:
    """Get the global configuration singleton"""
    return Settings()


# Create a global configuration instance
settings = get_settings()
