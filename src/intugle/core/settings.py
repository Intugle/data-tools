#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from intugle.core.project import Project
from intugle.core.utilities.configs import load_model_configuration, load_profiles_configuration

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


BASE_PATH = Path(__file__).resolve().parent.parent


def create_project_base_if_not_exists():
    """Create the base path directory if it does not exist."""
    project_base = Path(os.getenv("VSCODE_WORKSPACE", os.getcwd()), "intugle")
    if not project_base.exists():
        project_base.mkdir(parents=True, exist_ok=True)
    return str(project_base)


class Settings(BaseSettings):
    """Global Configuration"""

    UPSTREAM_SAMPLE_LIMIT: int = 10
    MODEL_DIR_PATH: str = str(
        Path(os.path.split(os.path.abspath(__file__))[0]).parent.joinpath("artifacts")
    )
    MODEL_RESULTS_PATH: str = os.path.join("model", "model_results")

    DI_CONFIG: dict = load_model_configuration("DI", {})
    KI_CONFIG: dict = load_model_configuration("KI", {})
    BG_CONFIG: dict = load_model_configuration("BG", {})

    DI_MODEL_VERSION: str = "13052023"

    # DIRECTORY STRUCTURE ENVS
    PROJECT_BASE: str = create_project_base_if_not_exists()
    PROJECT_ID: str = Project(PROJECT_BASE).project_id
    MODELS_DIR_NAME: str = "models"
    GRAPH_DIR_NAME: str = "kg"
    MODELS_DIR: str = os.path.join(PROJECT_BASE, MODELS_DIR_NAME)
    GRAPH_DIR: str = os.path.join(PROJECT_BASE, GRAPH_DIR_NAME)
    DESCRIPTIONS_DIR: str = os.path.join(PROJECT_BASE, "descriptions")

    def set_project_base(self, project_base: str):
        self.PROJECT_BASE = project_base
        self.PROJECT_ID = Project(self.PROJECT_BASE).project_id
        self.MODELS_DIR = os.path.join(self.PROJECT_BASE, self.MODELS_DIR_NAME)
        self.GRAPH_DIR = os.path.join(self.PROJECT_BASE, self.GRAPH_DIR_NAME)
        self.DESCRIPTIONS_DIR = os.path.join(self.PROJECT_BASE, "descriptions")

    PROFILES_PATH: str = os.path.join(os.getcwd(), "profiles.yml")
    PROFILES: dict = load_profiles_configuration(PROFILES_PATH)

    MCP_SERVER_NAME: str = "intugle"
    MCP_SERVER_DESCRIPTION: str = "Data Tools for MCP"
    MCP_SERVER_VERSION: str = "1.0.0"
    MCP_SERVER_AUTHOR: str = "Intugle"
    MCP_SERVER_STATELESS_HTTP: bool = True

    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = 8080
    MCP_SERVER_LOG_LEVEL: str = "info"

    SQL_DIALECT: str = "postgresql"
    DOMAIN: str = "ecommerce"
    UNIVERSAL_INSTRUCTIONS: str = ""
    L2_SAMPLE_LIMIT: int = 10

    # LLM CONFIGS
    LLM_PROVIDER: Optional[str] = None
    LLM_SAMPLE_LIMIT: int = 15
    STRATA_SAMPLE_LIMIT: int = 4
    MAX_RETRIES: int = 5
    SLEEP_TIME: int = 25
    ENABLE_RATE_LIMITER: bool = False
    CUSTOM_LLM_INSTANCE: Optional[Any] = None
    CUSTOM_EMBEDDINGS_INSTANCE: Optional[Any] = None

    # LP
    RELATIONSHIPS_FILE: str = "__relationships__.yml"
    HALLUCINATIONS_MAX_RETRY: int = 2
    UNIQUENESS_THRESHOLD: float = 0.9
    INTERSECT_RATIO_THRESHOLD: float = 0.9

    # DATETIME
    DATE_TIME_FORMAT_LIMIT: int = 25
    REMOVE_DATETIME_LP: bool = False

    L2_SAMPLE_LIMIT: int = 10

    # LLM CONFIGS
    LLM_TYPE: str = "azure"
    LLM_SAMPLE_LIMIT: int = 15
    STRATA_SAMPLE_LIMIT: int = 4

    # Adapter
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = "localhost"
    POSTGRES_DB: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_SCHEMA: Optional[str] = "public"

    # Vector
    VECTOR_COLLECTION_NAME: str = os.getcwd().split("/")[-1]
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    EMBEDDING_MODEL_NAME: str = "openai:ada"
    TOKENIZER_MODEL_NAME: str = "cl100k_base"

    # NETWORKX GRAPH
    NETWORKX_GRAPH_TOP_K_COLUMN: int = 4
    NETWORKX_GRAPH_MAX_DEPTH_COLUMN: int = 4
    NETWORKX_GRAPH_TOP_K_TABLE: int = 2
    NETWORKX_GRAPH_MAX_DEPTH_TABLE: int = 2

    # Langfuse Observability Settings
    LANGFUSE_ENABLED: bool = Field(default=False, description="Enable Langfuse tracing.")
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(None, description="Public key for Langfuse.")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(None, description="Secret key for Langfuse.")
    LANGFUSE_HOST: Optional[str] = Field("https://cloud.langfuse.com", description="Host for Langfuse.")

    model_config = SettingsConfigDict(
        env_file=f"{BASE_PATH}/.env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get the global configuration singleton"""
    return Settings()


# Create a global configuration instance
settings = get_settings()
