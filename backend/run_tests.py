#!/usr/bin/env python3
"""
Test runner script with various testing options
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print the result"""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")
    
    return result.returncode == 0

def main():
    """Main test runner"""
    print("🧪 Word Filter API Test Suite")
    print("=" * 60)
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    test_commands = [
        # Quick unit tests
        (["python", "-m", "pytest", "tests/", "-v", "-m", "unit"], 
         "Running Unit Tests"),
        
        # Integration tests
        (["python", "-m", "pytest", "tests/", "-v", "-m", "integration"], 
         "Running Integration Tests"),
        
        # Performance tests (slow)
        (["python", "-m", "pytest", "tests/", "-v", "-m", "performance", "--durations=5"], 
         "Running Performance Tests"),
        
        # Full test suite with coverage
        (["python", "-m", "pytest", "tests/", "-v", "--cov=main", "--cov-report=term", "--cov-report=html"], 
         "Running Full Test Suite with Coverage"),
        
        # Test specific modules
        (["python", "-m", "pytest", "tests/test_api_endpoints.py", "-v"], 
         "Testing API Endpoints"),
        
        (["python", "-m", "pytest", "tests/test_word_processing.py", "-v"], 
         "Testing Word Processing Logic"),
    ]
    
    # Allow user to choose which tests to run
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            commands_to_run = [test_commands[0]]
        elif test_type == "integration":
            commands_to_run = [test_commands[1]]
        elif test_type == "performance":
            commands_to_run = [test_commands[2]]
        elif test_type == "coverage":
            commands_to_run = [test_commands[3]]
        elif test_type == "api":
            commands_to_run = [test_commands[4]]
        elif test_type == "processing":
            commands_to_run = [test_commands[5]]
        elif test_type == "all":
            commands_to_run = test_commands
        else:
            print(f"Unknown test type: {test_type}")
            print("Available options: unit, integration, performance, coverage, api, processing, all")
            return
    else:
        # Default to unit and integration tests
        commands_to_run = test_commands[:2]
    
    # Run selected tests
    all_passed = True
    for cmd, description in commands_to_run:
        success = run_command(cmd, description)
        if not success:
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests PASSED!")
    else:
        print("💥 Some tests FAILED!")
    
    print("\n📊 Test Coverage Report:")
    print("   - HTML report: htmlcov/index.html")
    print("   - Logs: logs/")
    print("\n📝 Usage:")
    print("   python run_tests.py [unit|integration|performance|coverage|api|processing|all]")

if __name__ == "__main__":
    main()
