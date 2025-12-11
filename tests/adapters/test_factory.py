from intugle.adapters.factory import AdapterFactory, is_safe_plugin_name


def test_is_safe_plugin_name():
    """
    Tests the helper function for plugin security checks.
    """
    # Test valid plugins
    assert is_safe_plugin_name("intugle.adapters.types.snowflake.snowflake") is True
    assert is_safe_plugin_name("intugle.adapters.types.pandas.pandas") is True
    
    # Test invalid/unsafe plugins
    assert is_safe_plugin_name("malicious.plugin") is False
    assert is_safe_plugin_name("intugle.adapters.other.something") is False
    assert is_safe_plugin_name("") is False


def test_factory_initialization():
    """
    Tests that the factory still initializes correctly with default plugins.
    """
    factory = AdapterFactory()
    assert factory is not None
    # Ensure standard plugins are loaded (Pandas is usually default)
    assert "pandas" in factory.dataframe_funcs