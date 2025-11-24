
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.mysql import models as mysql_models
from intugle.adapters.types.mysql import mysql as mysql_module


def test_mysql_models_validation():
    cfg = {"identifier": "my_table", "type": "mysql"}
    parsed = mysql_models.MySQLConfig.model_validate(cfg)
    assert parsed.identifier == "my_table"


def test_can_handle_mysql():
    cfg = {"identifier": "my_table", "type": "mysql"}
    assert mysql_module.can_handle_mysql(cfg) is True


def test_register_no_error():
    factory = AdapterFactory(plugins=[])
    # calling register should not raise even if mysql deps are not installed
    mysql_module.register(factory)
