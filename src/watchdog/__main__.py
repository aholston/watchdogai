#!/usr/bin/env python3
"""
WatchDogAI main entry point

Alternative way to run: python main.py <command>
"""

import sys
from pathlib import Path

# Add src to path so we can import watchdog
sys.path.insert(0, str(Path(__file__).parent / "src"))

from watchdog.cli import main

if __name__ == "__main__":
    main()