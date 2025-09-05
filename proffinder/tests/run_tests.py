#!/usr/bin/env python3
"""
Test runner for ProfFinder tests.

Usage:
    python tests/run_tests.py
"""

import sys
import os
import pytest

def main():
    """Run all tests."""
    # Add the parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run pytest with verbose output
    test_args = [
        "-v",  # Verbose
        "--tb=short",  # Shorter traceback format
        "-x",  # Stop on first failure
        os.path.dirname(__file__)  # Test directory
    ]
    
    print("Running ProfFinder tests...")
    print("=" * 50)
    
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
    else:
        print("\n" + "=" * 50)
        print("❌ Some tests failed!")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())