from pydantic import BaseModel, Field, SecretStr
from typing import Optional, List


class RedshiftConfig(BaseModel):
    """
    Connection configuration for Amazon Redshift.
    Mirrors the structure of PostgresConfig but adds Redshift-specific fields.
    """

    host: str = Field(..., description="Redshift cluster endpoint")
    port: int = Field(default=5439, description="Default Redshift port")
    database: str = Field(..., description="Database name")
    user: Optional[str] = Field(None, description="Database user")
    password: Optional[SecretStr] = Field(
        None, description="Password for database user"
    )

    # Redshift-specific options
    iam: bool = Field(
        default=False,
        description="Enable IAM authentication instead of username/password",
    )
    cluster_id: Optional[str] = Field(
        default=None,
        description="Cluster identifier (required for IAM auth)",
    )
    region: Optional[str] = Field(
        default=None,
        description="AWS region of the Redshift cluster (for IAM auth)",
    )

    ssl: bool = Field(default=True, description="Enable SSL for secure connection")
    connect_timeout: int = Field(
        default=10, description="Connection timeout in seconds"
    )


class RedshiftDataConfig(BaseModel):
    """
    Optional data configuration for Redshift operations.
    Specifies schema and additional settings for Intugle data operations.
    """

    schema: str = Field(
        default="public",
        description="Default schema to operate in",
    )

    diststyle: Optional[str] = Field(
        default=None,
        description="Redshift table distribution style (AUTO, EVEN, KEY, ALL)",
    )
    distkey: Optional[str] = Field(
        default=None,
        description="Distribution key column name",
    )
    sortkeys: Optional[List[str]] = Field(
        default=None,
        description="Sort key columns for the table",
    )

