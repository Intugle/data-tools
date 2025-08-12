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
    LP_CONFIG: dict = load_model_configuration('LP', {})

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
    LLM_SAMPLE_LIMIT: int = 15
    STRATA_SAMPLE_LIMIT: int = 4

    # LP
    HALLUCINATIONS_MAX_RETRY: int = 2
    UNIQUENESS_THRESHOLD: float = 0.9

    # DATETIME
    DATE_TIME_FORMAT_LIMIT: int = 25
    REMOVE_DATETIME_LP: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get the global configuration singleton"""
    return Settings()


# Create a global configuration instance
settings = get_settings()
