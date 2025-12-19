"""Verify BigQueryAdapter implements all abstract methods from Adapter base class."""
from intugle.adapters.adapter import Adapter
from intugle.adapters.types.bigquery.bigquery import BigQueryAdapter
import inspect

# Get all abstract methods from Adapter
adapter_methods = {
    name for name, method in inspect.getmembers(Adapter, predicate=inspect.isfunction)
    if not name.startswith('_')
}

# Get all abstract properties from Adapter
adapter_properties = {
    name for name, prop in inspect.getmembers(Adapter, predicate=lambda x: isinstance(x, property))
    if not name.startswith('_')
}

# Check BigQueryAdapter has all methods
bq_methods = {
    name for name, method in inspect.getmembers(BigQueryAdapter, predicate=inspect.isfunction)
    if not name.startswith('_')
}

bq_properties = {
    name for name, prop in inspect.getmembers(BigQueryAdapter, predicate=lambda x: isinstance(x, property))
    if not name.startswith('_')
}

missing_methods = adapter_methods - bq_methods
missing_properties = adapter_properties - bq_properties

print("=" * 60)
print("ABSTRACT METHOD IMPLEMENTATION VERIFICATION")
print("=" * 60)
print(f"\nAdapter abstract methods: {len(adapter_methods)}")
print(f"Adapter abstract properties: {len(adapter_properties)}")
print(f"\nBigQueryAdapter methods: {len(bq_methods)}")
print(f"BigQueryAdapter properties: {len(bq_properties)}")

if missing_methods:
    print(f"\n❌ MISSING METHODS: {missing_methods}")
else:
    print(f"\n✅ All abstract methods implemented!")

if missing_properties:
    print(f"❌ MISSING PROPERTIES: {missing_properties}")
else:
    print(f"✅ All abstract properties implemented!")

# List all required methods
print("\n" + "=" * 60)
print("REQUIRED METHODS FROM ADAPTER BASE CLASS:")
print("=" * 60)
for method in sorted(adapter_methods):
    status = "✅" if method in bq_methods else "❌"
    print(f"{status} {method}")

print("\n" + "=" * 60)
print("REQUIRED PROPERTIES FROM ADAPTER BASE CLASS:")
print("=" * 60)
for prop in sorted(adapter_properties):
    status = "✅" if prop in bq_properties else "❌"
    print(f"{status} {prop}")

# Exit with error code if any missing
if missing_methods or missing_properties:
    exit(1)
else:
    print("\n" + "=" * 60)
    print("✅ ALL REQUIREMENTS MET!")
    print("=" * 60)
    exit(0)
