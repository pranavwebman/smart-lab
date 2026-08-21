"""
Database Engine & Session Setup with SQLite Foreign Keys enabled.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from pathlib import Path
from typing import Union
from app.config import get_db_path

Base = declarative_base()

def get_engine(db_path: Union[str, Path] = None):
    if db_path is None:
        db_path = get_db_path()

    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    return engine

def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
