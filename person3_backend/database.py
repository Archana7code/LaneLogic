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

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


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