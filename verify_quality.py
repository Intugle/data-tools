"""Verify all imports and registration work correctly."""
print("=" * 60)
print("CODE QUALITY AND IMPORT VERIFICATION")
print("=" * 60)

# Test 1: Models import
try:
    from intugle.adapters.types.bigquery.models import BigQueryConfig, BigQueryConnectionConfig
    print("\n✅ Models import successfully")
except Exception as e:
    print(f"\n❌ Models import failed: {e}")
    exit(1)

# Test 2: Adapter imports
try:
    from intugle.adapters.types.bigquery.bigquery import BigQueryAdapter, can_handle_bigquery, BIGQUERY_AVAILABLE
    print("✅ Adapter imports successfully")
    print(f"   - BigQuery dependencies available: {BIGQUERY_AVAILABLE}")
except Exception as e:
    print(f"❌ Adapter import failed: {e}")
    exit(1)

# Test 3: Factory registration
try:
    from intugle.adapters.factory import AdapterFactory
    factory = AdapterFactory()
    print("✅ Factory initialized")
    
    # Note: BigQuery adapter only registers if dependencies are installed
    if BIGQUERY_AVAILABLE:
        if "bigquery" in factory.dataframe_funcs:
            print("✅ BigQuery adapter registered in factory")
        else:
            print("❌ BigQuery adapter NOT registered in factory")
            exit(1)
    else:
        if "bigquery" not in factory.dataframe_funcs:
            print("✅ BigQuery adapter correctly NOT registered (dependencies not installed)")
        else:
            print("❌ BigQuery adapter incorrectly registered without dependencies")
            exit(1)
except Exception as e:
    print(f"❌ Factory initialization failed: {e}")
    exit(1)

# Test 4: Can handle function
try:
    valid_config = {"identifier": "test_table", "type": "bigquery"}
    invalid_config = {"type": "postgres"}
    
    assert can_handle_bigquery(valid_config) == True, "Should accept valid BigQuery config"
    assert can_handle_bigquery(invalid_config) == False, "Should reject non-BigQuery config"
    print("✅ can_handle_bigquery() works correctly")
except Exception as e:
    print(f"❌ can_handle_bigquery() failed: {e}")
    exit(1)

# Test 5: Model validation
try:
    config = BigQueryConfig(identifier="test_table", type="bigquery")
    assert config.identifier == "test_table"
    assert config.type == "bigquery"
    print("✅ BigQueryConfig model validation works")
    
    conn_config = BigQueryConnectionConfig(
        project_id="test-project",
        dataset="test_dataset"
    )
    assert conn_config.project_id == "test-project"
    assert conn_config.dataset_id == "test_dataset"
    assert conn_config.location == "US"
    print("✅ BigQueryConnectionConfig model validation works")
except Exception as e:
    print(f"❌ Model validation failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL QUALITY CHECKS PASSED!")
print("=" * 60)
print("\nSummary:")
print("- ✅ All imports work correctly")
print("- ✅ Factory registration successful")
print("- ✅ Config validation works")
print("- ✅ Dependency checking works")
print("- ✅ Ready for production use")
