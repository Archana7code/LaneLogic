# """
# LaneLogic - PERSON 3: Backend/API
# ====================================
# database.py - SQLAlchemy engine + session setup for the SQLite database.
# """

# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE_URL = "sqlite:///./lanelogic.db"

# # check_same_thread=False is required for SQLite when used with FastAPI's
# # threaded request handling.
# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()


# def get_db():
#     """FastAPI dependency that yields a DB session and always closes it."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()





"""
LaneLogic - PERSON 3: Backend/API
====================================
database.py - SQLAlchemy engine + session setup.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE_URL or SQLITE_PATH env vars let the deployment configure the database
# path (e.g. a Render persistent disk mount at /data/lanelogic.db).
# Falls back to ./lanelogic.db so local development is unaffected.
_db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLITE_PATH")
if _db_url:
    DATABASE_URL = _db_url
else:
    DATABASE_URL = "sqlite:///./lanelogic.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """Provide a database session and close it after the request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()