"""
pytest conftest — 确保 orchestration / ledger 作为 package 可 import。
"""
import sys
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
