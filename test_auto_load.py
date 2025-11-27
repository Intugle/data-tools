#!/usr/bin/env python3
"""
Test script for the auto-load datasets from directory feature.
"""
import sys
import os

# Add src to path to import intugle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from intugle.semantic_model import SemanticModel

def test_auto_load():
    """Test loading datasets from test_data directory."""
    try:
        # Test with our test_data folder
        sm = SemanticModel("test_data")
        
        print(f"Loaded datasets: {list(sm.datasets.keys())}")
        print(f"Number of datasets created: {len(sm.datasets)}")
        
        # Verify both CSV files were loaded
        assert "users" in sm.datasets, "users.csv should be loaded as 'users' dataset"
        assert "orders" in sm.datasets, "orders.csv should be loaded as 'orders' dataset"
        
        print("✅ Auto-loading feature works correctly!")
        return True
    
    except Exception as e:
        print(f"❌ Error testing auto-load feature: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_invalid_folder():
    """Test with invalid folder path."""
    try:
        sm = SemanticModel("nonexistent_folder")
        print("❌ Should have failed with invalid folder path")
        return False
    except (FileNotFoundError, NotADirectoryError):
        print("✅ Correctly handled invalid folder path")
        return True
    except Exception as e:
        print(f"❌ Unexpected error with invalid folder: {e}")
        return False

def test_empty_folder():
    """Test with empty directory (create one)."""
    try:
        empty_dir = "empty_test_dir"
        os.makedirs(empty_dir, exist_ok=True)
        
        try:
            sm = SemanticModel(empty_dir)
            print("❌ Should have failed with empty directory")
            return False
        except FileNotFoundError:
            print("✅ Correctly handled empty directory")
            return True
        except Exception as e:
            print(f"❌ Unexpected error with empty directory: {e}")
            return False
        finally:
            # Clean up
            if os.path.exists(empty_dir):
                os.rmdir(empty_dir)
    
    except Exception as e:
        print(f"❌ Error testing empty directory: {e}")
        return False

if __name__ == "__main__":
    print("Testing auto-load datasets feature...")
    
    success = True
    success &= test_auto_load()
    success &= test_invalid_folder()
    success &= test_empty_folder()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
