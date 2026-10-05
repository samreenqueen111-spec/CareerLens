"""
App-level database forwarding module for CareerLens.
"""

from database.database import get_db, init_db, close_db, get_db_path, close_connection
from database.models import AnalysisModel, UserModel, DatabaseError

__all__ = [
    "get_db",
    "init_db",
    "close_db",
    "get_db_path",
    "close_connection",
    "AnalysisModel",
    "UserModel",
    "DatabaseError"
]
