#!/usr/bin/env python3
"""Test the WatchDogAI CLI interface"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, expect_success=True):
    """Run a CLI command and check result"""
    print(f"\n🧪 Testing: {' '.join(cmd)}")
    
    try:
        # Set PYTHONPATH to include src directory
        env = dict(os.environ)
        src_path = str(Path.cwd() / "src")
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = src_path
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=Path.cwd(),
            env=env
        )
        
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if expect_success and result.returncode != 0:
            print("❌ Command failed unexpectedly")
            return False
        elif not expect_success and result.returncode == 0:
            print("⚠️  Command succeeded when failure was expected")
            return False
        else:
            print("✅ Command result as expected")
            return True
            
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    print("🧪 Testing WatchDogAI CLI Interface\n")
    
    # Test commands
    tests = [
        # Help commands
        ([sys.executable, "-m", "watchdog"], True),
        ([sys.executable, "-m", "watchdog", "--help"], True),
        
        # Status command
        ([sys.executable, "-m", "watchdog", "status"], True),
        
        # Search existing logs
        ([sys.executable, "-m", "watchdog", "search", "failed login"], True),
        
        # Analyze sample log file
        ([sys.executable, "-m", "watchdog", "analyze", "data/logs/sample_logs.txt"], True),
        
        # Test with non-existent file (should fail gracefully)
        ([sys.executable, "-m", "watchdog", "analyze", "nonexistent.log"], False),
        
        # Generate report
        ([sys.executable, "-m", "watchdog", "report", "--output", "test_report.md"], True),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, expect_success in tests:
        if run_command(cmd, expect_success):
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All CLI tests passed!")
        
        # Show what files were created
        print("\n📁 Generated files:")
        if Path("test_report.md").exists():
            size = Path("test_report.md").stat().st_size
            print(f"   test_report.md ({size} bytes)")
    else:
        print("❌ Some tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)