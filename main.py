#!/usr/bin/env python3
"""
main.py
Clean desktop GUI entry point for file_checker.
"""
import sys
import os

# Add directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.app import main

if __name__ == "__main__":
    main()
