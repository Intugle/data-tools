import os

from unittest.mock import patch

import pytest

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.oracle import models as oracle_models
from intugle.adapters.types.oracle import oracle as oracle_module
from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.semantic_model import SemanticModel

# --- Unit Tests ---


def test_oracle_connection_config_validation():
    # Test valid config with service_name
    valid_cfg_service = {
        "user": "admin",
        "password": "password",
        "host": "localhost",
        "service_name": "ORCL"
    }
    parsed_service = oracle_models.OracleConnectionConfig.model_validate(valid_cfg_service)
    assert parsed_service.service_name == "ORCL"
    assert parsed_service.port == 1521

    # Test valid config with SID
    valid_cfg_sid = {
        "user": "admin",
        "password": "password",
        "host": "localhost",
        "sid": "xe"
    }
    parsed_sid = oracle_models.OracleConnectionConfig.model_validate(valid_cfg_sid)
    assert parsed_sid.sid == "xe"

    # Test missing service_name AND sid
    invalid_cfg = {
        "user": "admin",
        "password": "password",
        "host": "localhost"
    }
    with pytest.raises(ValueError, match="Either 'service_name' or 'sid' must be provided"):
        oracle_models.OracleConnectionConfig.model_validate(invalid_cfg)


def test_oracle_config_validation():
    cfg = {"identifier": "MY_TABLE", "type": "oracle"}
    parsed = oracle_models.OracleConfig.model_validate(cfg)
    assert parsed.identifier == "MY_TABLE"
    assert parsed.type == "oracle"


def test_can_handle_oracle():
    cfg = {"identifier": "MY_TABLE", "type": "oracle"}
    assert oracle_module.can_handle_oracle(cfg) is True


def test_register_no_error():
    # Only runs if oracledb is installed (mocked here if needed or relying on environment)
    # If environment doesn't have it, register does nothing, which is also "no error".
    factory = AdapterFactory(plugins=[])
    oracle_module.register(factory)


# --- Live Integration Tests (Guarded) ---

RUN_LIVE_TESTS = os.getenv("INTUGLE_RUN_LIVE_TESTS", "false").lower() == "true"


@pytest.fixture(scope="module")
def oracle_setup():
    if not RUN_LIVE_TESTS:
        yield None
        return

    try:
        import oracledb
    except ImportError:
        pytest.skip("oracledb not installed")

    oracle_config = settings.PROFILES.get("oracle")
    if not oracle_config:
        pytest.skip("No 'oracle' config found in profiles.yml")

    # Connect
    try:
        user = oracle_config.get("user")
        password = oracle_config.get("password")
        host = oracle_config.get("host")
        port = oracle_config.get("port", 1521)
        service_name = oracle_config.get("service_name")
        sid = oracle_config.get("sid")
        
        dsn = None
        if service_name:
            dsn = f"{host}:{port}/{service_name}"
        elif sid:
            dsn = oracledb.makedsn(host, port, sid=sid)
            
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        cursor = conn.cursor()
    except Exception as e:
        pytest.skip(f"Could not connect to Oracle: {e}")

    # Setup Tables
    prefix = "INTUGLE_TEST"
    
    # Oracle doesn't support IF EXISTS in DROP TABLE standardly in older versions, using exception block often needed
    # but we will try creating.
    def drop_table(name):
        try:
            cursor.execute(f"DROP TABLE {name}")
        except oracledb.DatabaseError:
            pass
            
    tables_ddl = {
        f"{prefix}_USERS": f"""
            CREATE TABLE {prefix}_USERS (
                ID NUMBER PRIMARY KEY,
                NAME VARCHAR2(100),
                EMAIL VARCHAR2(100)
            )
        """,
        f"{prefix}_ORDERS": f"""
            CREATE TABLE {prefix}_ORDERS (
                ORDER_ID NUMBER PRIMARY KEY,
                USER_ID NUMBER,
                AMOUNT NUMBER(10, 2)
            )
        """
    }

    created_tables = []
    try:
        for name, ddl in tables_ddl.items():
            drop_table(name)
            cursor.execute(ddl)
            created_tables.append(name)
        
        # Insert Data
        cursor.execute(f"INSERT INTO {prefix}_USERS VALUES (1, 'Alice', 'alice@example.com')")
        cursor.execute(f"INSERT INTO {prefix}_USERS VALUES (2, 'Bob', 'bob@example.com')")
        cursor.execute(f"INSERT INTO {prefix}_ORDERS VALUES (101, 1, 50.00)")
        cursor.execute(f"INSERT INTO {prefix}_ORDERS VALUES (102, 1, 25.00)")
        cursor.execute(f"INSERT INTO {prefix}_ORDERS VALUES (103, 2, 100.00)")
        conn.commit()
        
        yield {
            "tables": created_tables,
            "prefix": prefix,
            "config": oracle_config
        }
        
    finally:
        # Cleanup
        # Close adapter connection if open
        try:
            if oracle_module.OracleAdapter._instance and oracle_module.OracleAdapter._instance.connection:
                oracle_module.OracleAdapter._instance.connection.close()
        except Exception:
            pass

        try:
            cursor.execute(f"DROP VIEW {prefix}_USERS_VIEW")
        except Exception:
            pass

        for name in reversed(created_tables):
            drop_table(name)
        
        conn.close()


@pytest.mark.skipif(not RUN_LIVE_TESTS, reason="Live tests not enabled")
def test_oracle_end_to_end(oracle_setup, tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    with patch("intugle.core.settings.settings.MODELS_DIR", str(models_dir)):
        # 1. Setup Semantic Model
        datasets = []
        for table in oracle_setup["tables"]:
            ds_data = oracle_models.OracleConfig(identifier=table, type="oracle")
            datasets.append(DataSet(data=ds_data, name=table))
            
        sm = SemanticModel(datasets, domain="Oracle Test")
        sm.build()
        
        assert len(sm.profiling_df) > 0
        users_profile = sm.profiling_df[sm.profiling_df['table_name'] == f"{oracle_setup['prefix']}_USERS"]
        assert not users_profile.empty
        # Check count
        assert users_profile.iloc[0]['count'] == 2

