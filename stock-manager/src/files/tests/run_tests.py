"""
tests/run_tests.py — Test runner for Stock Manager Pro.

Runs all unit tests using unittest framework (no pytest required).
"""
from __future__ import annotations

import sys
import os
import unittest
import tempfile

# Add src/files to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress logs during tests
import logging
logging.disable(logging.CRITICAL)


def run_tests():
    """Discover and run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover all test files
    test_dir = os.path.dirname(os.path.abspath(__file__))
    discovered = loader.discover(test_dir, pattern="test_*.py")
    suite.addTests(discovered)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
