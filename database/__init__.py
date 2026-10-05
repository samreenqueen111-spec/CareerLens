"""
Database module for CareerLens AI (Stage 7).
Provides database connection, table initialization, and AnalysisModel entity.
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
