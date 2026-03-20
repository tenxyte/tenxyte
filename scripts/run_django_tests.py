"""
Test Runner for Tenxyte Django Integration Tests

This script runs the complete Django test suite to verify zero regression
after the framework-agnostic refactoring.

Usage:
    python scripts/run_django_tests.py

Requirements:
    - Django installed
    - pytest-django installed
    - Database configured (SQLite by default for tests)

Exit codes:
    0 - All tests passed
    1 - Some tests failed
    2 - Test configuration error
"""

import subprocess
import sys
import os
from pathlib import Path


def run_django_tests():
    """Run the Django integration test suite."""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("=" * 80)
    print("TENXYTE DJANGO TEST SUITE - REGRESSION CHECK")
    print("=" * 80)
    print()
    print("This script verifies that all Django tests pass after refactoring.")
    print("Zero breaking changes should be introduced.")
    print()
    
    # Test configuration
    test_path = "tests/integration/django/"
    django_settings = "tests.integration.django.settings"
    
    # Run tests with pytest
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--reuse-db",
        "--create-db",
        f"--ds={django_settings}",
        "-x",  # Stop on first failure
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    print("-" * 80)
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    print()
    print("-" * 80)
    print()
    
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED - No regressions detected!")
        print()
        print("The Django test suite completed successfully.")
        print("This confirms backward compatibility is maintained.")
    else:
        print(f"❌ TESTS FAILED (exit code: {result.returncode})")
        print()
        print("Some tests failed. Please review the output above.")
    
    return result.returncode


def run_test_summary():
    """Generate a summary of test coverage."""
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    # Count test files
    test_dirs = {
        "Core Tests": "tests/core/",
        "Django Integration": "tests/integration/django/",
    }
    
    for name, path in test_dirs.items():
        test_files = list(Path(path).rglob("test_*.py"))
        print(f"  {name}: {len(test_files)} test files")
    
    print()
    print("Key requirements for zero regression:")
    print("  ✓ All existing tests must pass")
    print("  ✓ No test files should be modified")
    print("  ✓ No test assertions should be weakened")
    print("  ✓ API contracts remain unchanged")
    print()


if __name__ == "__main__":
    exit_code = run_django_tests()
    run_test_summary()
    sys.exit(exit_code)
