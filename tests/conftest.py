"""
Pytest configuration and shared fixtures.
"""
import pytest
import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
